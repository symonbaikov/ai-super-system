const DEFAULT_HEADERS = {
  'content-type': 'application/json',
}

async function handleResponse(response) {
  if (!response.ok) {
    const text = await response.text()
    throw new Error(text || `Request failed: ${response.status}`)
  }
  const contentType = response.headers.get('content-type') || ''
  if (contentType.includes('application/json')) {
    return response.json()
  }
  return response.text()
}

export async function fetchAlerts(apiBase) {
  const response = await fetch(`${apiBase}/api/alerts`)
  return handleResponse(response)
}

export async function runParserJob(apiBase, payload) {
  const response = await fetch(`${apiBase}/api/parser/run`, {
    method: 'POST',
    headers: DEFAULT_HEADERS,
    body: JSON.stringify(payload),
  })
  return handleResponse(response)
}

export async function acknowledgeAlert(apiBase, alertId) {
  const response = await fetch(`${apiBase}/api/alerts/${alertId}/ack`, {
    method: 'POST',
    headers: DEFAULT_HEADERS,
  })
  return handleResponse(response)
}

export async function exportAlerts(apiBase) {
  const response = await fetch(`${apiBase}/api/alerts`)
  const data = await handleResponse(response)
  return JSON.stringify(data, null, 2)
}

export async function requestAdvice(apiBase, payload) {
  const response = await fetch(`${apiBase}/api/advice`, {
    method: 'POST',
    headers: DEFAULT_HEADERS,
    body: JSON.stringify(payload),
  })
  return handleResponse(response)
}
