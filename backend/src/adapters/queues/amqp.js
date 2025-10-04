import amqp from 'amqplib'

export async function createAMQP(name='sp', handler){
  const url = process.env.RABBITMQ_URL || 'amqp://guest:guest@localhost:5672'
  const conn = await amqp.connect(url)
  const ch = await conn.createChannel()
  await ch.assertQueue(name, { durable: true })
  if(handler){
    ch.consume(name, async msg=>{
      if(!msg) return
      const data = JSON.parse(msg.content.toString('utf-8'))
      try { await handler({ name, data }); ch.ack(msg) } catch(e){ ch.nack(msg, false, true) }
    })
  }
  return {
    add: async (type, data)=> ch.sendToQueue(name, Buffer.from(JSON.stringify({ type, data })))
  }
}
