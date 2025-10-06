import { randomUUID } from 'crypto'

import { fetchRugCheck } from '../../adapters/security/rugcheck.js'
import { fetchSniffer } from '../../adapters/security/sniffer.js'
import { bus } from '../../server/sse.js'
import { METRICS } from '../../monitoring/prometheus.js'
import { postAlert, postTradeConfirm } from '../alerts.js'

const APIFY_BASE = (process.env.APIFY_BASE_URL || 'https://api.apify.com').replace(/\/$/, '')
const APIFY_TOKEN = process.env.APIFY_TOKEN
const APIFY_ACTOR_ID = process.env.APIFY_ACTOR_ID

async function getFetch(){
  if (typeof fetch === 'function') return fetch
  const mod = await import('node-fetch')
  return mod.default
}

export function summarizeRisk({ rugcheck, sniffer }){
  const issues = []
  if(rugcheck?.risk && ['high', 'critical', 'red', 'severe'].includes(String(rugcheck.risk).toLowerCase())){
    issues.push('rugcheck')
  }
  if(typeof sniffer?.score === 'number' && sniffer.score < 40){
    issues.push('sniffer')
  }
  return {
    severity: issues.length >= 2 ? 'critical' : issues.length === 1 ? 'warn' : 'info',
    issues,
  }
}

async function triggerApify(symbol, metadata){
  if(!APIFY_TOKEN || !APIFY_ACTOR_ID){
    return { skipped: true }
  }
  const fetchImpl = await getFetch()
  const payload = {
    input: {
      symbol,
      metadata,
    },
    token: APIFY_TOKEN,
  }
  const res = await fetchImpl(`${APIFY_BASE}/v2/acts/${APIFY_ACTOR_ID}/runs?wait=0`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if(!res.ok){
    const text = await res.text()
    throw new Error(`apify http ${res.status} ${text}`)
  }
  return await res.json()
}

export async function handleParserRun(job){
  const data = job.data || {}
  const symbol = (data.symbol || '').toUpperCase()
  const mint = data.metadata?.mint || data.metadata?.address || symbol
  const sources = data.sources || []
  const filters = data.filters || []

  METRICS.ingested.inc()

  const [rugcheck, sniffer] = await Promise.all([
    fetchRugCheck(mint, { endpoint: process.env.RUGCHECK_API_URL || undefined }).catch(err => ({ risk: 'unknown', score: null, error: String(err) })),
    fetchSniffer(mint, { endpoint: process.env.SNIFFER_API_URL || undefined }).catch(err => ({ status: 'unknown', score: null, error: String(err) })),
  ])

  let apifyRun = null
  let simulatedTrade = null
  try{
    apifyRun = await triggerApify(symbol, data.metadata || {})
  }catch(err){
    METRICS.errors.inc()
    console.error('[worker] apify trigger failed', err)
  }

  bus.emit('signal', {
    kind: 'parser_job',
    t: Math.floor(Date.now()/1000),
    symbol,
    meta: {
      candidate_id: data.candidate_id,
      sources,
      filters,
      apifyRun,
      rugcheck,
      sniffer,
    },
  })

  const riskSummary = summarizeRisk({ rugcheck, sniffer })
  if(riskSummary.severity === 'info' && data.candidate_id){
    const tradePayload = {
      trade_id: randomUUID(),
      candidate_id: data.candidate_id,
      status: 'simulated_buy',
      executed_at: new Date().toISOString(),
      metadata: {
        symbol,
        sources,
        filters,
        risk: riskSummary,
        note: 'auto-simulated trade for demo flow',
      },
    }
    try{
      const response = await postTradeConfirm(tradePayload)
      if(response?.error){
        throw new Error(response.error)
      }
      simulatedTrade = response?.trade_id ? response : tradePayload
      bus.emit('signal', {
        kind: 'trade_simulated',
        t: Math.floor(Date.now()/1000),
        meta: {
          candidate_id: data.candidate_id,
          symbol,
          trade: simulatedTrade,
        },
      })
    }catch(err){
      METRICS.errors.inc()
      console.error('[worker] trade simulation failed', err)
    }
  }

  if(riskSummary.severity !== 'info'){
    await postAlert({
      title: `Risk ${riskSummary.severity.toUpperCase()} for ${symbol}`,
      severity: riskSummary.severity,
      source: 'worker',
      message: `Parser detected ${riskSummary.issues.join(' & ')} signals for ${symbol}`,
      payload: {
        candidate_id: data.candidate_id,
        rugcheck,
        sniffer,
        symbol,
      },
    })
  }

  return {
    ok: true,
    symbol,
    risk: riskSummary,
    apifyRun,
    simulatedTrade,
  }
}
