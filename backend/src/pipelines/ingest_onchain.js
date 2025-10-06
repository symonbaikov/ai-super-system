// Ingest on-chain events and candles from Helius/QuickNode (Solana first pass)
import { HeliusProvider } from '../providers/helius.js'
import { QuickNodeProvider } from '../providers/quicknode.js'
import { SolClient } from '../adapters/chain/solana.js'
import { METRICS } from '../monitoring/prometheus.js'

const buildCandle = (price, volume) => {
  const base = price ?? 1 + Math.random() * 0.05
  return {
    t: Math.floor(Date.now() / 1000),
    o: base * 0.998,
    h: base * 1.002,
    l: base * 0.996,
    c: base,
    v: volume ?? Math.round(500 + Math.random() * 250),
  }
}

export async function runIngestOnchain({ mintList = [], intervalMs = 5000 } = {}) {
  const heliusKey = process.env.HELIUS_API_KEY
  const rawQuicknodeUrl = process.env.QUICKNODE_URL
  const quicknodeToken = process.env.QUICKNODE_TOKEN

  // drop placeholder QuickNode endpoints so we do not hammer an invalid host
  const quicknodeUrl = rawQuicknodeUrl && !rawQuicknodeUrl.includes('example.quicknode.com')
    ? rawQuicknodeUrl
    : ''

  const helius = heliusKey ? new HeliusProvider(heliusKey) : null
  const quicknode = quicknodeUrl ? new QuickNodeProvider(quicknodeUrl, quicknodeToken) : null
  const sol = new SolClient(process.env.RPC_URL || quicknodeUrl || '')

  const store = new Map() // key: mint -> candles[]

  async function collectForMint(mint) {
    let price = null
    let activityCount = 0

    if (quicknode) {
      try {
        const { price: p } = await quicknode.getTokenPrice(mint)
        if (Number.isFinite(p) && p > 0) {
          price = p
        }
      } catch (err) {
        console.error('[quicknode]', mint, err.message)
      }
    }

    if (helius) {
      try {
        const signatures = await helius.getTokenActivity(mint)
        activityCount = Array.isArray(signatures) ? signatures.length : 0
      } catch (err) {
        console.error('[helius]', mint, err.message)
      }
    }

    const candle = buildCandle(price, activityCount)
    const arr = store.get(mint) || []
    arr.push({ ...candle, priceSource: price ? 'quicknode' : 'synthetic', activityCount })
    if (arr.length > 300) arr.shift()
    store.set(mint, arr)
    METRICS.ingested.inc()
  }

  async function tick() {
    for (const mint of mintList) {
      await collectForMint(mint)
    }
    setTimeout(() => {
      tick().catch((err) => console.error('[ingest_onchain]', err))
    }, intervalMs)
  }

  // start loop without awaiting to avoid blocking caller
  tick().catch((err) => console.error('[ingest_onchain:init]', err))

  return {
    getCandles: (mint) => store.get(mint) || [],
    getBalance: (address) => sol.getBalance(address),
  }
}
