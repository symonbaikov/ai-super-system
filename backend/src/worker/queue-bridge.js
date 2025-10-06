import IORedis from 'ioredis'

const delay = (ms)=> new Promise(resolve=> setTimeout(resolve, ms))

export class RedisBullBridge {
  constructor({ redisUrl, namespace = 'sp', logger = console } = {}){
    this.redis = new IORedis(redisUrl || process.env.REDIS_URL || 'redis://localhost:6379', {
      maxRetriesPerRequest: null,
    })
    this.namespace = namespace
    this.logger = logger
    this.targets = new Map()
    this.running = false
    this.tasks = []
  }

  register(sourceName, bullQueue){
    this.targets.set(sourceName, bullQueue)
  }

  async start(){
    if(this.running) return
    this.running = true
    for(const [name, queue] of this.targets.entries()){
      this.tasks.push(this.#consumeLoop(name, queue))
    }
  }

  async stop(){
    this.running = false
    await Promise.allSettled(this.tasks)
    this.tasks = []
    try{
      await this.redis.quit()
    }catch(err){
      this.logger.error('[bridge] redis quit error', err)
    }
  }

  async #consumeLoop(name, queue){
    const key = `${this.namespace}:queue:${name}`
    while(this.running){
      try{
        const result = await this.redis.blpop(key, 5)
        if(!result){
          continue
        }
        const [, raw] = result
        let job
        try{
          job = JSON.parse(raw)
        }catch(err){
          this.logger.error('[bridge] failed to parse job', err, raw)
          continue
        }
        const payload = job.payload ?? job
        const opts = {
          removeOnComplete: true,
          attempts: 3,
          backoff: { type: 'exponential', delay: 5000 },
        }
        if(job.id){
          opts.jobId = job.id
        }
        await queue.add(name, payload, opts)
      }catch(err){
        if(!this.running) break
        this.logger.error('[bridge] consume error', err)
        await delay(1000)
      }
    }
  }
}
