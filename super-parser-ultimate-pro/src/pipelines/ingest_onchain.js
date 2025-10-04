// Ingest on-chain events and candles from Helius/QuickNode (Solana first pass)
import { HeliusProvider } from '../providers/helius.js'
import { SolClient } from '../adapters/chain/solana.js'
import { METRICS } from '../monitoring/prometheus.js'

const toCandle = (tx)=>{
  // placeholder: real mapping from tx/price feed to candle
  // {t,o,h,l,c,v}
  const t = Math.floor(Date.now()/1000)
  const c = 1 + Math.random()*0.05
  return { t, o:c*0.998, h:c*1.002, l:c*0.996, c, v: Math.round(1000+Math.random()*500) }
}

export async function runIngestOnchain({mintList=[], intervalMs=5000}={}){
  const helius = new HeliusProvider(process.env.HELIUS_API_KEY||'')
  const sol = new SolClient(process.env.RPC_URL||'')

  const store = new Map() // key: mint -> candles[]
  async function tick(){
    for(const mint of mintList){
      // const activity = await helius.getTokenActivity(mint)
      const candle = toCandle()
      const arr = store.get(mint)||[]
      arr.push(candle)
      if(arr.length>300) arr.shift()
      store.set(mint, arr)
      METRICS.ingested.inc()
    }
    setTimeout(tick, intervalMs)
  }
  tick()

  return {
    getCandles: (mint)=> store.get(mint)||[]
  }
}
