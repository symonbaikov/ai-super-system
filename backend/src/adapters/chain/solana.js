import { Connection, PublicKey } from '@solana/web3.js'

export class SolClient {
  constructor(rpc){ this.conn = new Connection(rpc||'https://api.mainnet-beta.solana.com', 'confirmed') }
  async getBalance(addr){
    try { return await this.conn.getBalance(new PublicKey(addr)) } catch(e){ return null }
  }
}
