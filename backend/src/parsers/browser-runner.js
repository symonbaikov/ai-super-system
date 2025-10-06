const interval = parseInt(process.env.PARSER_BROWSER_POLL_MS || '10000', 10)
console.log('[parser-browser] starting poller, interval=%dms', interval)

setInterval(() => {
  console.log('[parser-browser] heartbeat', new Date().toISOString())
}, interval)

process.on('SIGTERM', () => {
  console.log('[parser-browser] shutting down')
  process.exit(0)
})
