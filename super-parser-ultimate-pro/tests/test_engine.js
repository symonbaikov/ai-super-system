// quick unit test for signal engine
import { computeSignals } from '../src/signals/engine.js'

// make fake candles with a pump then dump
const candles = []
let price = 1.0
for(let i=0;i<120;i++){
  if(i===60) price*=1.12  // pump 12%
  if(i===90) price*=0.86  // dump 14% from pumped level
  const o=price*(0.995+Math.random()*0.01)
  const c=price*(0.995+Math.random()*0.01)
  const h=Math.max(o,c)* (1.001+Math.random()*0.005)
  const l=Math.min(o,c)* (0.999-Math.random()*0.005)
  const v=Math.round(1000 + Math.random()*500 + (i===60?1500:0) + (i===90?1500:0))
  candles.push({ t: Date.now()/1000 + i*60, o,h,l,c,v })
  price = c
}

const sigs = computeSignals(candles, { pumpJumpPct: 6, dumpDropPct: 6 })
console.log('signals:', sigs.slice(-10))
console.log('count=', sigs.length)
if(!sigs.length) process.exit(1)
