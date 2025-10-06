import { summarizeRisk } from '../src/worker/handlers/parser-run.js'

const lowRisk = summarizeRisk({ rugcheck: { risk: 'low' }, sniffer: { score: 90 } })
if(lowRisk.severity !== 'info'){
  console.error('expected info severity for low risk')
  process.exit(1)
}

const mediumRisk = summarizeRisk({ rugcheck: { risk: 'critical' }, sniffer: { score: 90 } })
if(mediumRisk.severity !== 'warn'){
  console.error('expected warn severity when only one provider flags risk')
  process.exit(1)
}

const highRisk = summarizeRisk({ rugcheck: { risk: 'red' }, sniffer: { score: 20 } })
if(highRisk.severity !== 'critical'){
  console.error('expected critical severity when both providers flag risk')
  process.exit(1)
}

console.log('worker risk summary tests passed')
