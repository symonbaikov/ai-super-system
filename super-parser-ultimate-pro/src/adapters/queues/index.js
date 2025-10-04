import { createBull } from './bullmq.js'
import { createAMQP } from './amqp.js'

export async function createQueue(name, handler){
  const backend = (process.env.QUEUE_BACKEND||'redis').toLowerCase()
  if(backend === 'rabbitmq') return createAMQP(name, async job=> handler(job))
  // bullmq
  return createBull(name, async job=> handler({ name: job.name, data: job.data }))
}
