// Detect 'whale in' events from on-chain candles/flows (stub logic)
import { bus } from '../server/sse.js'
import { METRICS } from '../monitoring/prometheus.js'

/**
 * crude whale detector: volume spike vs moving average
 * @param {{getCandles:Function}} onchain
 */
export function runWhales(onchain, {mints=[], lookback=30, volX=3}={}){
  setInterval(()=>{
    for(const mint of mints){
      const arr = onchain.getCandles(mint)
      if(arr.length<lookback+1) continue
      const last = arr[arr.length-1]
      const base = arr.slice(-lookback-1,-1).reduce((s,x)=>s+(x.v||0),0)/lookback
      if(last.v && base && last.v > base*volX){
        bus.emit('signal', { kind:'whale_in', t:last.t, price:last.c, strength: Math.min(1,last.v/(base*volX)), meta:{mint, vol:last.v, base} })
        METRICS.signals.inc()
      }
    }
  }, 6000)
}
