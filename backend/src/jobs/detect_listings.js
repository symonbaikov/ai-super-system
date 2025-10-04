// Detect listing/relisting/delisting events and emit annotations
import { bus } from '../server/sse.js'
import { METRICS } from '../monitoring/prometheus.js'

/**
 * watch a CEX ingest snapshot provider and emit 'listing' signals
 * @param {{snapshot:Function}} cex
 */
export function runDetectListings(cex){
  let seen = new Set()
  setInterval(()=>{
    const now = Date.now()
    const snap = cex.snapshot()
    for(const r of snap){
      const id = `${r.exchange}:${r.status}:${Math.floor(r.ts/60000)}`
      if(!seen.has(id) && (r.status==='live'||r.status==='scheduled')){
        seen.add(id)
        bus.emit('signal', { kind:'listing', t:Math.floor(now/1000), price:r.price||0, strength:0.7, meta:{exchange:r.exchange,status:r.status} })
        METRICS.signals.inc()
      }
    }
  }, 5000)
}
