import { RSI, EMA, SMA, BollingerBands } from 'technicalindicators'
import { METRICS } from '../monitoring/prometheus.js'

/**
 * Compute signals on candle series.
 * @param {Array<{t:number,o:number,h:number,l:number,c:number,v:number}>} candles sorted by time asc
 * @param {Object} opts {pumpJumpPct, dumpDropPct, rsiOverbought, rsiOversold}
 * @returns {Signal[]} list of signals
 */
export function computeSignals(candles, opts={}){
  const O = Object.assign({ pumpJumpPct: 5, dumpDropPct: 5, rsiOverbought: 75, rsiOversold: 30 }, opts)
  if(!candles || candles.length<30) return []
  const closes = candles.map(k=>k.c)
  const volumes = candles.map(k=>k.v||0)
  const rsi = RSI.calculate({ period: 14, values: closes })
  const ema20 = EMA.calculate({ period: 20, values: closes })
  const sma50 = SMA.calculate({ period: 50, values: closes })
  const bb = BollingerBands.calculate({ period: 20, values: closes, stdDev: 2 })

  const sigs = []
  for(let i=1;i<candles.length;i++){
    const a=candles[i-1], b=candles[i]
    const pct = (b.c - a.c)/a.c*100
    const volSpike = b.v && a.v ? (b.v > a.v*2.5) : false
    const rs = rsi[i- (candles.length - rsi.length)] // align index (rsi shorter)
    const bbIdx = i - (candles.length - bb.length)
    const bbv = bbIdx>=0? bb[bbIdx] : null

    // Pump/Dump heuristics
    if(pct >= O.pumpJumpPct && (rs||0) > O.rsiOverbought-5){
      sigs.push({ kind:'pump', t:b.t, price:b.c, strength: Math.min(1, pct/10), meta:{pct, rs, volSpike} })
    }
    if(pct <= -O.dumpDropPct && (rs||100) < O.rsiOversold+5){
      sigs.push({ kind:'dump', t:b.t, price:b.c, strength: Math.min(1, Math.abs(pct)/10), meta:{pct, rs, volSpike} })
    }

    // Entry/Exit with BB & EMA cross (very simple)
    const ema = ema20[i-(candles.length-ema20.length)]
    const sma = sma50[i-(candles.length-sma50.length)]
    if(ema && sma){
      const prevE = ema20[i-1-(candles.length-ema20.length)]
      const prevS = sma50[i-1-(candles.length-sma50.length)]
      if(prevE && prevS){
        if(prevE<=prevS && ema> sma){
          sigs.push({ kind:'entry', t:b.t, price:b.c, strength:0.6, meta:{reason:'ema20 cross up sma50'} })
        }
        if(prevE>=prevS && ema< sma){
          sigs.push({ kind:'exit', t:b.t, price:b.c, strength:0.6, meta:{reason:'ema20 cross down sma50'} })
        }
      }
    }

    // BB bounce pattern
    if(bbv && (b.c<=bbv.lower || b.c>=bbv.upper)){
      sigs.push({ kind:'pattern', t:b.t, price:b.c, strength:0.4, meta:{bb: bbv, side: b.c<=bbv.lower?'lower':'upper'} })
    }
  }
  METRICS.signals.inc(sigs.length)
  return sigs
}
