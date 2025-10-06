import express from 'express'

const app = express()
const port = parseInt(process.env.PARSER_HTTP_PORT || '9100', 10)

app.use(express.json({ limit: '1mb' }))

app.get('/health', (_req, res) => {
  res.json({ ok: true, service: 'parser-http' })
})

app.post('/parse', (req, res) => {
  const payload = req.body || {}
  console.log('[parser-http] received payload', JSON.stringify(payload).slice(0, 500))
  res.json({ ok: true, received: payload })
})

app.listen(port, () => {
  console.log(`[parser-http] listening on ${port}`)
})
