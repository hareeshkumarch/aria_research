import { useCallback, useRef } from 'react'
import { useARIAStore } from '../store'
import type { ARIAEvent } from '../types'

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''

export function useRunStream() {
  const { startRun, handleEvent, setGoal, setStreamStatus } = useARIAStore()
  const sourceRef = useRef<EventSource | null>(null)

  const startAgent = useCallback(async (goal: string, mode: string = "fast", modelStr: string = "groq/llama-3.3-70b-versatile") => {
    setGoal(goal)

    let provider = undefined;
    let model = modelStr;
    if (modelStr.includes('/')) {
      const parts = modelStr.split('/');
      provider = parts[0];
      model = parts[1];
    }

    // 1. Create the run
    const res = await fetch(`${API_BASE}/api/v1/runs`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ goal, mode, model, provider }),
    })

    if (!res.ok) {
      const errText = await res.text()
      let errMsg = errText
      try {
        const parsed = JSON.parse(errText)
        errMsg = parsed.detail?.error || (typeof parsed.detail === 'string' ? parsed.detail : errText)
      } catch (e) { }
      throw new Error(errMsg)
    }

    const { run_id } = await res.json()
    startRun(run_id, goal, mode as 'fast' | 'deep')

    // 2. Open SSE stream with reconnection
    connectSSE(run_id)
  }, [startRun, handleEvent, setGoal, setStreamStatus])

  const connectSSE = useCallback((runId: string, attempt = 0) => {
    // Close any previous stream before creating a new one
    if (sourceRef.current) {
      try { sourceRef.current.close() } catch { }
    }

    setStreamStatus(attempt === 0 ? 'connected' : 'reconnecting', attempt)

    const source = new EventSource(`${API_BASE}/api/v1/runs/${runId}/stream`)
    sourceRef.current = source
    let closed = false

    const EVENTS = [
      'run_start', 'node_start', 'node_done', 'plan_ready',
      'tool_call', 'tool_retry', 'token', 'run_complete', 'run_error',
      'memory_recall', 'memory_store', 'critic_score', 'cost_update',
      'run_paused', 'run_resumed', 'run_aborted', 'tool_result',
      // New pipeline events
      'goal_understood', 'reasoning_complete', 'node_timing', 'metrics_update'
    ]

    EVENTS.forEach((evtType) => {
      source.addEventListener(evtType, (e: MessageEvent) => {
        try {
          const data: ARIAEvent = JSON.parse(e.data)
          handleEvent(data)
        } catch (_) {
          // ignore parse errors
        }
      })
    })

    source.addEventListener('done', () => {
      closed = true
      source.close()
      if (sourceRef.current === source) sourceRef.current = null
    })

    source.onerror = () => {
      source.close()
      if (sourceRef.current === source) sourceRef.current = null

      // Don't reconnect if the stream closed normally
      if (closed) return

      // Reconnect with exponential backoff (max 3 attempts)
      if (attempt < 3) {
        const delay = Math.min(1000 * Math.pow(2, attempt), 8000)
        console.warn(`SSE connection lost. Reconnecting in ${delay}ms (attempt ${attempt + 1})...`)
        setStreamStatus('reconnecting', attempt + 1)
        setTimeout(() => connectSSE(runId, attempt + 1), delay)
      } else {
        console.error('SSE connection failed after 3 attempts.')
        setStreamStatus('disconnected', attempt)
        handleEvent({ type: 'run_error', error: 'Lost connection to server. Please try again.' })
      }
    }
  }, [handleEvent, setStreamStatus])

  const retryStream = useCallback(() => {
    const { runId, status } = useARIAStore.getState()
    if (!runId) return
    if (status !== 'running' && status !== 'paused') return
    connectSSE(runId, 0)
  }, [connectSSE])

  return { startAgent, retryStream }
}
