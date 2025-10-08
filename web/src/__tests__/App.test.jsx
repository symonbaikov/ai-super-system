import { render, screen } from '@testing-library/react'
import App from '../App.jsx'
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'

class MockEventSource {
  static instances = []

  constructor(url) {
    this.url = url
    this.readyState = 0
    this.onopen = null
    this.onmessage = null
    this.onerror = null
    MockEventSource.instances.push(this)
    queueMicrotask(() => {
      this.onopen?.({})
    })
  }

  emit(data) {
    this.onmessage?.({ data: JSON.stringify(data) })
  }

  fail(error = new Error('SSE error')) {
    this.onerror?.(error)
  }

  close() {
    this.readyState = 2
  }
}




describe('App smoke', () => {
  beforeEach(() => {
    MockEventSource.instances = []
    global.EventSource = MockEventSource
    global.fetch = vi.fn(async () => ({
      ok: true,
      headers: { get: (name) => (name === 'content-type' ? 'application/json' : null) },
      json: async () => ([]),
      text: async () => '[]'
    }))
  })

  afterEach(() => {
    vi.restoreAllMocks()
    delete global.EventSource
    delete global.fetch
  })

  it('renders main header', async () => {
    render(<App />)
    expect(await screen.findByText('Super Parser AI — интерфейс')).toBeInTheDocument()
  })
})
