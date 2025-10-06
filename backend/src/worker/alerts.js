const FASTAPI_BASE = (process.env.FASTAPI_URL || process.env.API_BASE_URL || 'http://localhost:9000').replace(/\/$/, '')

async function getFetch(){
  if (typeof fetch === 'function') return fetch
  const mod = await import('node-fetch')
  return mod.default
}

async function postJson(path, payload){
  if(!FASTAPI_BASE){
    return { skipped: true }
  }
  try{
    const fetchImpl = await getFetch()
    const res = await fetchImpl(`${FASTAPI_BASE}${path}`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(payload),
    })
    const text = await res.text()
    if(!res.ok){
      throw new Error(`http ${res.status} ${text}`)
    }
    if(!text){
      return null
    }
    try{
      return JSON.parse(text)
    }catch(parseErr){
      return text
    }
  }catch(err){
    console.error('[fastapi] request failed', path, err)
    return { error: String(err) }
  }
}

export async function postAlert(payload){
  return postJson('/api/alerts', payload)
}

export async function postTradeConfirm(payload){
  return postJson('/api/trade/confirm', payload)
}
