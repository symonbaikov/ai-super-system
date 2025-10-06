import 'dotenv/config'
import express from 'express'
import cors from 'cors'
import fetch from 'node-fetch'
import { initProm } from './monitoring/prometheus.js'
import { initSentry } from './monitoring/sentry.js'
import { createQueue } from './adapters/queues/index.js'
import { computeSignals } from './signals/engine.js'
import { bus } from './server/sse.js'
import { startWorkers } from './worker/index.js'

const app = express()
app.use(cors())
app.use(express.json())

await initSentry()
await initProm(parseInt(process.env.METRICS_PORT||'9110'))

// queue for ingest->signals
const q = await createQueue('sp-signals', async (job)=>{
  try{
    const { candles } = job.data || {}
    if(!Array.isArray(candles) || candles.length<10) return null
    const sigs = computeSignals(candles)
    sigs.forEach(s=> bus.emit('signal', s))
    return { count: sigs.length }
  }catch(e){
    console.error('worker error', e)
    return null
  }
})

// routes
app.get('/status', (_,res)=> res.json({ ok:true, ts: Date.now() }))

// accept candles and return signals immediately
app.post('/signals/analyze', async (req,res)=>{
  const { candles, options } = req.body||{}
  const out = computeSignals(candles||[], options||{})
  res.json({ signals: out })
})

// proxy to Golib AI (3 models) – unified entry
app.post('/advice', async (req,res)=>{
  try{
    const url = process.env.GOLIB_URL
    if(!url) return res.status(400).json({error:'GOLIB_URL not set'})
    const r = await fetch(url+'/advice', { method:'POST', headers:{'content-type':'application/json','x-api-key':process.env.GOLIB_KEY||''}, body: JSON.stringify(req.body||{}) })
    const j = await r.json()
    res.json(j)
  }catch(e){ res.status(500).json({error:String(e)}) }
})

import { mountSSE } from './server/sse.js'
mountSSE(app)

const port = parseInt(process.env.PORT||'8811')
app.listen(port, ()=> console.log('[super-parser-ultimate] up on', port))

const workerController = await startWorkers()
const shutdown = async ()=>{
  try { await workerController?.stop?.() } catch(err){ console.error('[worker] shutdown error', err) }
  process.exit(0)
}
process.on('SIGINT', shutdown)
process.on('SIGTERM', shutdown)

// ---- pipelines & jobs wiring (demo) ----
import { runIngestOnchain } from './pipelines/ingest_onchain.js'
import { runIngestCEX } from './pipelines/ingest_cex.js'
import { runDetectListings } from './jobs/detect_listings.js'
import { runWhales } from './jobs/whales.js'
import fs from 'fs'

// load presets
function loadJSON(p){ try{ return JSON.parse(fs.readFileSync(p,'utf-8')) }catch{return null} }
const platforms = loadJSON('./configs/platforms.json')
const accounts = loadJSON('./configs/accounts.json')
const rules = loadJSON('./configs/rules.json')

console.log('[presets] platforms=', platforms?.cex?.length, 'accounts.t1=', accounts?.twitter_influencers_tier1?.length)

// start ingestors
const oc = await runIngestOnchain({ mintList: (process.env.MINTS||'So11111111111111111111111111111111111111112').split(','), intervalMs: 5000 })
const cx = await runIngestCEX({ tickers: (process.env.TICKERS||'PEPE,DEGEN').split(','), intervalMs: 8000 })

// attach jobs
runDetectListings(cx)
runWhales(oc, { mints: (process.env.MINTS||'So11111111111111111111111111111111111111112').split(','), lookback: 20, volX: 3 })
