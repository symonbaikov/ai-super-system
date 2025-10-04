import { EventEmitter } from 'events'
export const bus = new EventEmitter()

export function mountSSE(app){
  app.get('/stream', (req,res)=>{
    res.setHeader('Content-Type','text/event-stream')
    res.setHeader('Cache-Control','no-cache')
    res.setHeader('Connection','keep-alive')
    const onEvent = (e)=> res.write(`data: ${JSON.stringify(e)}\n\n`)
    bus.on('signal', onEvent)
    req.on('close', ()=> bus.off('signal', onEvent))
  })
}
