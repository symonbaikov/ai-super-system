import { createPublicClient, http } from 'viem'
import { mainnet } from 'viem/chains'

export class EVMClient {
  constructor(rpc){ this.client = createPublicClient({ chain: mainnet, transport: http(rpc) }) }
  async getBlockNumber(){ return await this.client.getBlockNumber() }
}
