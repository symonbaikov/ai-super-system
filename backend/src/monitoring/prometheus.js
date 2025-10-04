import http from 'http'
import client from 'prom-client'

export async function initProm(port=9110){
  client.collectDefaultMetrics()
  const register = client.register
  const server = http.createServer(async (req,res)=>{
    if(req.url==='/metrics'){
      res.setHeader('Content-Type', register.contentType)
      res.end(await register.metrics())
    } else {
      res.statusCode = 404; res.end('not found')
    }
  })
  server.listen(port)
  return { register, server }
}

export const METRICS = {
  ingested: new client.Counter({ name:'sp_ingested_events_total', help:'Ingested events' }),
  signals: new client.Counter({ name:'sp_signals_total', help:'Produced trading signals' }),
  errors: new client.Counter({ name:'sp_errors_total', help:'Errors' }),
}
