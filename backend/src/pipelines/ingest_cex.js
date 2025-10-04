// Ingest CEX listings and prices (Binance/OKX/Bybit/MEXC/Gate/HTX)
import { METRICS } from '../monitoring/prometheus.js'
import { getListings, getPrice } from '../adapters/price/cex.js'

export async function runIngestCEX({tickers=[], intervalMs=8000}={}){
  const state = new Map() // ticker -> { exchange, status, price, ts }
  async function loop(){
    for(const t of tickers){
      // 1) listings
      const listings = await getListings(t) // TODO: plug real API
      for(const L of (listings||[])){
        state.set(`${L.exchange}:${t}`, {...L, ts: Date.now()})
        METRICS.ingested.inc()
      }
      // 2) prices
      for(const ex of ["Binance","OKX","Bybit","MEXC","Gate","HTX"]){
        const p = await getPrice(ex, t) // TODO: plug real API
        if(p) state.set(`${ex}:${t}`, {exchange: ex, status:'live', price: p, ts: Date.now()})
      }
    }
    setTimeout(loop, intervalMs)
  }
  loop()
  return {
    snapshot: ()=> Array.from(state.entries()).map(([k,v])=> ({key:k, ...v}))
  }
}
