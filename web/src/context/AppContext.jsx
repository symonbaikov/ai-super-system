import React, { createContext, useContext, useEffect, useMemo, useReducer } from 'react'
import { fetchAlerts, runParserJob, acknowledgeAlert, requestAdvice } from '../lib/api.js'

const STREAM_URL = import.meta.env.VITE_STREAM_URL || 'http://localhost:8811/stream'

const initialState = {
  currentTab: 'start',
  connection: { status: 'idle', lastEventAt: null },
  signals: [],
  alerts: [],
  advice: null,
  loading: { parser: false, alerts: false, advice: false },
  error: null,
}

function reducer(state, action) {
  switch (action.type) {
    case 'SET_TAB':
      return { ...state, currentTab: action.tab }
    case 'SET_CONNECTION':
      return { ...state, connection: action.payload }
    case 'ADD_SIGNAL': {
      const next = [action.payload, ...state.signals]
      return { ...state, signals: next.slice(0, 200) }
    }
    case 'SET_ALERTS':
      return { ...state, alerts: action.payload, loading: { ...state.loading, alerts: false } }
    case 'SET_ADVICE':
      return { ...state, advice: action.payload, loading: { ...state.loading, advice: false } }
    case 'UPDATE_ALERT': {
      const alerts = state.alerts.map(alert => alert.id === action.payload.id ? action.payload : alert)
      return { ...state, alerts }
    }
    case 'SET_LOADING':
      return { ...state, loading: { ...state.loading, ...action.payload } }
    case 'SET_ERROR':
      return { ...state, error: action.payload }
    default:
      return state
  }
}

const AppContext = createContext(null)

export function AppProvider({ children }) {
  const [state, dispatch] = useReducer(reducer, initialState)
  const apiBase = useMemo(() => import.meta.env.VITE_API_URL || 'http://localhost:9000', [])

  useEffect(() => {
    let cancelled = false

    async function loadAlerts() {
      dispatch({ type: 'SET_LOADING', payload: { alerts: true } })
      try {
        const data = await fetchAlerts(apiBase)
        if (!cancelled) {
          dispatch({ type: 'SET_ALERTS', payload: data })
        }
      } catch (error) {
        if (!cancelled) {
          dispatch({ type: 'SET_LOADING', payload: { alerts: false } })
          dispatch({ type: 'SET_ERROR', payload: error instanceof Error ? error.message : String(error) })
        }
      }
    }

    loadAlerts()

    return () => {
      cancelled = true
    }
  }, [apiBase])

  useEffect(() => {
    const source = new EventSource(STREAM_URL)
    dispatch({ type: 'SET_CONNECTION', payload: { status: 'connecting', lastEventAt: null } })

    source.onopen = () => {
      dispatch({ type: 'SET_CONNECTION', payload: { status: 'open', lastEventAt: null } })
    }

    source.onerror = () => {
      dispatch({ type: 'SET_CONNECTION', payload: { status: 'error', lastEventAt: Date.now() } })
    }

    source.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data)
        dispatch({ type: 'ADD_SIGNAL', payload })
        dispatch({ type: 'SET_CONNECTION', payload: { status: 'open', lastEventAt: Date.now() } })
      } catch (error) {
        dispatch({ type: 'SET_ERROR', payload: error instanceof Error ? error.message : String(error) })
      }
    }

    return () => {
      source.close()
    }
  }, [STREAM_URL])

  const actions = useMemo(() => ({
    setTab: (tab) => dispatch({ type: 'SET_TAB', tab }),
    refreshAlerts: async () => {
      dispatch({ type: 'SET_LOADING', payload: { alerts: true } })
      try {
        const data = await fetchAlerts(apiBase)
        dispatch({ type: 'SET_ALERTS', payload: data })
      } catch (error) {
        dispatch({ type: 'SET_LOADING', payload: { alerts: false } })
        dispatch({ type: 'SET_ERROR', payload: error instanceof Error ? error.message : String(error) })
      }
    },
    runParser: async (payload) => {
      dispatch({ type: 'SET_LOADING', payload: { parser: true } })
      try {
        await runParserJob(apiBase, payload)
      } catch (error) {
        dispatch({ type: 'SET_ERROR', payload: error instanceof Error ? error.message : String(error) })
      } finally {
        dispatch({ type: 'SET_LOADING', payload: { parser: false } })
      }
    },
    fetchAdvice: async (prompt, metadata = {}) => {
      dispatch({ type: 'SET_LOADING', payload: { advice: true } })
      try {
        const result = await requestAdvice(apiBase, { prompt, metadata })
        dispatch({ type: 'SET_ADVICE', payload: result })
      } catch (error) {
        dispatch({ type: 'SET_LOADING', payload: { advice: false } })
        dispatch({ type: 'SET_ERROR', payload: error instanceof Error ? error.message : String(error) })
      }
    },
    acknowledgeAlert: async (alertId) => {
      try {
        const updated = await acknowledgeAlert(apiBase, alertId)
        dispatch({ type: 'UPDATE_ALERT', payload: updated })
      } catch (error) {
        dispatch({ type: 'SET_ERROR', payload: error instanceof Error ? error.message : String(error) })
      }
    },
    clearError: () => dispatch({ type: 'SET_ERROR', payload: null }),
  }), [apiBase])

  const value = useMemo(() => ({ state, actions, apiBase }), [state, actions, apiBase])

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>
}

export function useAppContext() {
  const ctx = useContext(AppContext)
  if (!ctx) {
    throw new Error('useAppContext must be used within AppProvider')
  }
  return ctx
}
