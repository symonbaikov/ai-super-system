import fetch from 'node-fetch'

export class HeliusProvider {
  constructor(apiKey, options = {}) {
    this.apiKey = apiKey
    this.rpcEndpoint = options.rpcEndpoint || `https://mainnet.helius-rpc.com/?api-key=${apiKey}`
    this.restEndpoint = options.restEndpoint || 'https://api.helius.xyz'
    this.fetchImpl = options.fetch || fetch
    if (!this.apiKey) {
      throw new Error('HELIUS_API_KEY is required')
    }
  }

  async getTokenActivity(mint) {
    const body = {
      jsonrpc: '2.0',
      id: 1,
      method: 'getSignaturesForAddress',
      params: [mint, { limit: 25 }],
    }
    const response = await this.fetchImpl(this.rpcEndpoint, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(body),
    })
    if (!response.ok) {
      const text = await response.text()
      throw new Error(`Helius RPC error: ${response.status} ${text}`)
    }
    const data = await response.json()
    return data?.result ?? []
  }

  async getAddressTransactions(address) {
    const url = `${this.restEndpoint}/v0/addresses/${address}/transactions?api-key=${this.apiKey}&limit=25`
    const response = await this.fetchImpl(url)
    if (!response.ok) {
      const text = await response.text()
      throw new Error(`Helius REST error: ${response.status} ${text}`)
    }
    return await response.json()
  }
}
