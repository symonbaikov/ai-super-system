import { HeliusProvider } from '../src/providers/helius.js'
import { QuickNodeProvider } from '../src/providers/quicknode.js'

function createMockFetch(responders) {
  return async (url, options = {}) => {
    for (const { test, reply } of responders) {
      if (test(url, options)) {
        const { status = 200, body = {}, headers = {} } = await reply(url, options)
        return {
          ok: status >= 200 && status < 300,
          status,
          json: async () => body,
          text: async () => JSON.stringify(body),
          headers,
        }
      }
    }
    throw new Error(`No mock handler for ${url}`)
  }
}

async function testHelius() {
  const fixtures = {
    rpc: {
      jsonrpc: '2.0',
      result: [{ signature: 'abc', slot: 1 }],
    },
    rest: [{ signature: 'abc', timestamp: 1 }],
  }
  const fetchImpl = createMockFetch([
    {
      test: (url) => String(url).includes('mock.helius-rpc'),
      reply: async () => ({ body: fixtures.rpc }),
    },
    {
      test: (url) => String(url).includes('mock.helius-api'),
      reply: async () => ({ body: fixtures.rest }),
    },
  ])
  const provider = new HeliusProvider('abc123', { fetch: fetchImpl, rpcEndpoint: 'https://mock.helius-rpc/?api-key=abc123', restEndpoint: 'https://mock.helius-api' })
  const activity = await provider.getTokenActivity('So11111111111111111111111111111111111111112')
  if (!Array.isArray(activity) || activity.length !== 1) {
    throw new Error('Helius provider failed to return RPC data')
  }
  const restData = await provider.getAddressTransactions('So11111111111111111111111111111111111111112')
  if (!Array.isArray(restData) || restData.length !== 1) {
    throw new Error('Helius provider REST fetch failed')
  }
}

async function testQuickNode() {
  const fetchImpl = createMockFetch([
    {
      test: (url, opts) => String(url).includes('quicknode.example') && opts.method === 'POST',
      reply: async () => ({
        body: {
          result: [
            {
              mint: 'So11111111111111111111111111111111111111112',
              price: 1.23,
            },
          ],
        },
      }),
    },
  ])
  const provider = new QuickNodeProvider('https://quicknode.example', 'token123', { fetch: fetchImpl })
  const { price } = await provider.getTokenPrice('So11111111111111111111111111111111111111112')
  if (price !== 1.23) {
    throw new Error('QuickNode provider failed to parse price')
  }
}

async function run() {
  await testHelius()
  await testQuickNode()
  console.log('provider tests passed')
}

run().catch((err) => {
  console.error(err)
  process.exit(1)
})
