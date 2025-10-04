import { Queue, Worker } from 'bullmq'
import IORedis from 'ioredis'

export async function createBull(name='sp', handler){
  const connection = new IORedis(process.env.REDIS_URL || 'redis://localhost:6379')
  const q = new Queue(name, { connection })
  if(handler){
    new Worker(name, handler, { connection })
  }
  return q
}
