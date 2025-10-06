import Bullmq from 'bullmq'
import IORedis from 'ioredis'

const { Queue, Worker } = Bullmq

import { RedisBullBridge } from './queue-bridge.js'
import { handleParserRun } from './handlers/parser-run.js'
import { handleApifyDataset } from './handlers/apify-dataset.js'
import { handleHeliusEvent } from './handlers/helius-event.js'

const redisUrl = process.env.REDIS_URL || 'redis://localhost:6379'
const namespace = process.env.QUEUE_NAMESPACE || 'sp'
const prefix = process.env.BULLMQ_PREFIX || 'sp-worker'
const concurrency = Number(process.env.WORKER_CONCURRENCY || 2)

const connection = new IORedis(redisUrl, { maxRetriesPerRequest: null })

function buildQueue(name, processor){
  const queueName = `${prefix}:${name}`
  const queue = new Queue(queueName, { connection })
  const worker = new Worker(queueName, processor, { connection, concurrency })
  worker.on('failed', (job, err)=>{
    console.error(`[worker] ${name} failed`, job?.id, err)
  })
  worker.on('completed', (job)=>{
    if(process.env.DEBUG_WORKER === 'true'){
      console.log(`[worker] ${name} completed`, job?.id)
    }
  })
  return { queue, worker }
}

const parserQueue = buildQueue('parser-run', handleParserRun)
const apifyQueue = buildQueue('apify-dataset', handleApifyDataset)
const heliusQueue = buildQueue('helius-events', handleHeliusEvent)

const bridge = new RedisBullBridge({ redisUrl, namespace })
bridge.register('parser:run', parserQueue.queue)
bridge.register('apify:dataset', apifyQueue.queue)
bridge.register('helius:events', heliusQueue.queue)

export async function startWorkers(){
  await bridge.start()
  return {
    stop: async ()=>{
      await bridge.stop()
      await Promise.all([
        parserQueue.worker.close(),
        apifyQueue.worker.close(),
        heliusQueue.worker.close(),
        parserQueue.queue.close(),
        apifyQueue.queue.close(),
        heliusQueue.queue.close(),
      ])
      await connection.quit()
    }
  }
}
