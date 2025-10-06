import { bus } from '../../server/sse.js'
import { METRICS } from '../../monitoring/prometheus.js'
import { postAlert } from '../alerts.js'

const HIGH_VALUE_THRESHOLD = Number(process.env.HELIUS_HIGH_VALUE_SOL || 500)

export async function handleHeliusEvent(job){
  const data = job.data || {}
  METRICS.ingested.inc()
  const eventType = data.type || 'unknown'

  bus.emit('signal', {
    kind: 'helius_event',
    t: Math.floor(Date.now()/1000),
    meta: data,
  })

  const nativeTransfers = data.nativeTransfers || []
  const totalLamports = nativeTransfers.reduce((sum, item)=> sum + (item.amount || 0), 0)
  const SOL_PER_LAMPORT = 1_000_000_000
  const totalSol = totalLamports / SOL_PER_LAMPORT

  if(totalSol >= HIGH_VALUE_THRESHOLD){
    await postAlert({
      title: `Whale transfer ${totalSol.toFixed(2)} SOL`,
      severity: 'warn',
      source: 'helius',
      message: `Detected ${eventType} with volume ${totalSol.toFixed(2)} SOL`,
      payload: {
        event: eventType,
        account: data.account,
        transactionSignature: data.transactionSignature,
        totalSol,
      },
    })
  }

  return { ok: true, type: eventType, totalSol }
}
