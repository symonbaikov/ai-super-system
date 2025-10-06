import { render, screen, waitFor, fireEvent } from '@testing-library/react'
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

describe('App', () => {
  beforeEach(() => {
    MockEventSource.instances = []
    global.EventSource = MockEventSource
    global.fetch = vi.fn(async () => ({
      ok: true,
      headers: { get: (name) => (name === 'content-type' ? 'application/json' : null) },
      json: async () => [],
    }))
  })

  afterEach(() => {
    vi.restoreAllMocks()
    delete global.EventSource
    delete global.fetch
  })

  it('renders tabs and consumes SSE events', async () => {
    render(<App />)

    expect(screen.getByText('Super Parser AI — Control Center')).toBeInTheDocument()
    expect(screen.getByText('Старт')).toBeInTheDocument()

    await waitFor(() => {
      expect(screen.getAllByText('SSE подключено').length).toBeGreaterThan(0)
    })

    const [instance] = MockEventSource.instances
    expect(instance).toBeDefined()

    fireEvent.click(screen.getByText('Парсер'))

    instance.emit({
      kind: 'social_signal',
      meta: { source: 'test', mint: 'TEST' },
      t: 1_700_000_000,
    })

    await waitFor(() => expect(screen.getByText('social_signal')).toBeInTheDocument())
    await waitFor(() => expect(screen.getByText('TEST')).toBeInTheDocument())
  })
})
