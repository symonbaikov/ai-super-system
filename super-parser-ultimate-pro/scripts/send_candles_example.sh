#!/usr/bin/env bash
curl -s http://localhost:8811/signals/analyze -H 'content-type: application/json' -d @samples/candles.sample.json
