import IORedis from 'ioredis'

const redisUrl = process.env.REDIS_URL || 'redis://localhost:6379'
const namespace = process.env.QUEUE_NAMESPACE || 'sp'
const ttlSeconds = parseInt(process.env.WHALES_RESULT_TTL || '600', 10)

const redis = new IORedis(redisUrl, { maxRetriesPerRequest: null })

function randomFloat(min, max){
  return Math.random() * (max - min) + min
}

function pick(arr){
  return arr[Math.floor(Math.random() * arr.length)]
}

function generateEntries(filters = {}){
  const baseMint = filters.mint || 'So11111111111111111111111111111111111111112'
  const symbols = ['$TRUMP', '$DOGE', '$CAT', '$PEPE', '$ALPHA']
  const safetyOptions = [
    { rugcheck: 'ok', solsniffer: 'ok' },
    { rugcheck: 'ok', solsniffer: 'warn' },
    { rugcheck: 'warn', solsniffer: 'warn' },
  ]

  return Array.from({ length: 3 }).map((_, idx) => {
    const whales = 3 + idx + Math.floor(Math.random() * 3)
    const solSum = Number(randomFloat(filters.min_sol || 5, (filters.min_sol || 5) + 35).toFixed(2))
    const safety = pick(safetyOptions)
    const mint = baseMint.slice(0, 30) + String(idx)
    const hype = {
      tw_1h: 150 + Math.floor(Math.random() * 400),
      tg_1h: 80 + Math.floor(Math.random() * 220),
    }
    return {
      mint,
      name: `${pick(symbols)}${Math.floor(Math.random() * 100)}`,
      whales,
      sol_sum: solSum,
      safety,
      hype,
      links: {
        birdeye: `https://birdeye.so/token/${mint}?chain=solana`,
      },
    }
  })
}

export async function handleWhalesScan(job){
  const jobId = job.id || job.data?.jobId
  if(!jobId){
    throw new Error('missing job id')
  }
  const filters = job.data?.filters || {}
  const entries = generateEntries(filters)
  const payload = {
    jobId,
    generatedAt: new Date().toISOString(),
    items: entries.map((item)=> ({
      ...item,
      hype: {
        tw_1h: item.hype.tw_1h,
        tg_1h: item.hype.tg_1h,
      },
    })),
  }

  await redis.set(
    `${namespace}:whales:result:${jobId}`,
    JSON.stringify(payload),
    'EX',
    ttlSeconds,
  )
  await redis.hset(`${namespace}:whales:status:${jobId}`, {
    status: 'completed',
    updated_at: new Date().toISOString(),
  })
  await redis.expire(`${namespace}:whales:status:${jobId}`, ttlSeconds)

  return { count: entries.length }
}

export async function closeWhalesScanRedis(){
  try{
    await redis.quit()
  }catch(err){
    if(process.env.DEBUG_WORKER === 'true'){
      console.error('[worker] failed to quit whales redis', err)
    }
  }
}
