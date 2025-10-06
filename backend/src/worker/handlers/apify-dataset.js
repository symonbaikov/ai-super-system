import { bus } from '../../server/sse.js'
import { METRICS } from '../../monitoring/prometheus.js'
import { postAlert } from '../alerts.js'

export async function handleApifyDataset(job){
  const data = job.data || {}
  const items = data.dataset_items || []
  const candidateId = data.candidate_id

  for(const item of items){
    bus.emit('signal', {
      kind: 'social_signal',
      t: Math.floor(Date.now()/1000),
      meta: {
        candidate_id: candidateId,
        run_id: data.run_id,
        source: 'apify',
        item,
      },
    })
  }

  METRICS.ingested.inc(items.length || 1)

  if(data.status && data.status !== 'SUCCEEDED'){
    await postAlert({
      title: `Apify run ${data.status}`,
      severity: 'warn',
      source: 'apify',
      message: `Actor run ${data.run_id} finished with status ${data.status}`,
      payload: { candidate_id: candidateId, status: data.status },
    })
  }

  return { ok: true, items: items.length }
}
