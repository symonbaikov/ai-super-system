import fetch from 'node-fetch'

export class QuickNodeProvider {
  constructor(endpoint, token, options = {}) {
    this.endpoint = endpoint
    this.token = token
    this.fetchImpl = options.fetch || fetch
    if (!this.endpoint) {
      throw new Error('QUICKNODE_URL is required to use QuickNodeProvider')
    }
  }

  async getTokenPrice(mint) {
    const body = {
      jsonrpc: '2.0',
      id: 1,
      method: 'qn_getTokenPrice',
      params: [
        {
          currency: 'usd',
          tokens: [
            {
              mint,
            },
          ],
        },
      ],
    }
    const headers = { 'content-type': 'application/json' }
    if (this.token) {
      headers['x-qn-api-key'] = this.token
    }
    const response = await this.fetchImpl(this.endpoint, {
      method: 'POST',
      headers,
      body: JSON.stringify(body),
    })
    if (!response.ok) {
      const text = await response.text()
      throw new Error(`QuickNode error: ${response.status} ${text}`)
    }
    const data = await response.json()
    const list = Array.isArray(data?.result) ? data.result : []
    const priceEntry = list.find((item) => item?.mint === mint || item?.token === mint) || list[0] || {}
    const rawPrice = priceEntry?.price ?? priceEntry?.value
    const parsedPrice = typeof rawPrice === 'number' ? rawPrice : Number(rawPrice)
    return {
      price: Number.isFinite(parsedPrice) ? parsedPrice : null,
      raw: data,
    }
  }
}
