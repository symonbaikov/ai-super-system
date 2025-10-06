import { setTimeout as delay } from 'timers/promises'

const DEFAULT_ENDPOINT = 'https://api.rugcheck.xyz/v1/projects'

async function getFetch(){
  if (typeof fetch === 'function') return fetch
  const mod = await import('node-fetch')
  return mod.default
}

export async function fetchRugCheck(mint, { endpoint = DEFAULT_ENDPOINT, retries = 2 } = {}){
  const fetchImpl = await getFetch()
  const url = `${endpoint.replace(/\/$/, '')}/${encodeURIComponent(mint)}`
  let attempt = 0
  while(attempt <= retries){
    try{
      const res = await fetchImpl(url, { headers: { accept: 'application/json' } })
      if(!res.ok) throw new Error(`rugcheck http ${res.status}`)
      const data = await res.json()
      return {
        risk: data?.risk ?? data?.scoreLabel ?? 'unknown',
        score: data?.score ?? null,
        flags: data?.flags ?? [],
        raw: data,
      }
    }catch(err){
      if(attempt === retries) return { risk: 'unknown', score: null, flags: [], error: String(err) }
      await delay(250 * (attempt + 1))
    }
    attempt += 1
  }
  return { risk: 'unknown', score: null, flags: [] }
}
