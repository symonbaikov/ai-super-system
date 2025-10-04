import * as Sentry from '@sentry/node'

export async function initSentry(){
  if(!process.env.SENTRY_DSN) return
  Sentry.init({ dsn: process.env.SENTRY_DSN, tracesSampleRate: 0.1 })
  return Sentry
}
