import { setTimeout as delay } from 'timers/promises'

const DEFAULT_ENDPOINT = 'https://sniffer-api.up.railway.app/api/v1/mints'

async function getFetch(){
  if (typeof fetch === 'function') return fetch
  const mod = await import('node-fetch')
  return mod.default
}

export async function fetchSniffer(mint, { endpoint = DEFAULT_ENDPOINT, retries = 2 } = {}){
  const fetchImpl = await getFetch()
  const url = `${endpoint.replace(/\/$/, '')}/${encodeURIComponent(mint)}`
  let attempt = 0
  while(attempt <= retries){
    try{
      const res = await fetchImpl(url, { headers: { accept: 'application/json' } })
      if(res.status === 404) return { status: 'unknown', score: null, raw: null }
      if(!res.ok) throw new Error(`sniffer http ${res.status}`)
      const data = await res.json()
      return {
        status: data?.status ?? data?.label ?? 'unknown',
        score: data?.score ?? data?.trust ?? null,
        raw: data,
      }
    }catch(err){
      if(attempt === retries) return { status: 'unknown', score: null, error: String(err), raw: null }
      await delay(250 * (attempt + 1))
    }
    attempt += 1
  }
  return { status: 'unknown', score: null, raw: null }
}
