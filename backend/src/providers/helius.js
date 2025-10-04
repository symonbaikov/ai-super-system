import fetch from 'node-fetch'

export class HeliusProvider {
  constructor(key){ this.base = 'https://mainnet.helius-rpc.com/?api-key='+key }
  async getTokenActivity(mint){ /* map to your endpoint/model */ return { mint, txs: [] } }
}
