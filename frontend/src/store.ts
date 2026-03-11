import { create } from 'zustand'
import type { RunState, ARIAEvent, GraphNode, Subtask, CostData, CriticScore, GoalAnalysis, ReasoningOutput, RunHistoryItem, MemoryChunk } from './types'
import { sseParser } from './services/sseParser'

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''

interface ARIAStore extends RunState {
  setGoal: (goal: string) => void
  startRun: (runId: string, goal: string, mode?: 'fast' | 'deep') => void
  handleEvent: (event: ARIAEvent) => void
  setStreamStatus: (status: RunState['streamStatus'], attempt?: number) => void
  reset: () => void
  loadHistory: () => Promise<void>
  loadMemory: () => Promise<void>
  pauseRun: () => Promise<void>
  resumeRun: (directive?: string) => Promise<void>
  abortRun: () => Promise<void>
  deleteRun: (runId: string) => Promise<void>
  viewHistoryRun: (run: RunHistoryItem) => Promise<void>
}

const INITIAL_STATE: RunState = {
  runId: null,
  goal: '',
  status: 'idle',
  streamStatus: 'idle',
  streamAttempt: 0,
  graphNodes: [],
  subtasks: [],
  thoughtStream: '',
  finalOutput: '',
  errorMessage: '',
  costData: { input_tokens: 0, output_tokens: 0, total_cost: 0 },
  criticScore: null,
  goalAnalysis: null,
  reasoningOutput: null,
  runHistory: [],
  memoryChunks: [],
  currentMode: 'fast',
}

export const useARIAStore = create<ARIAStore>((set, get) => ({
  ...INITIAL_STATE,

  setGoal: (goal) => set({ goal }),

  startRun: (runId, goal, mode) =>
    set({
      runId,
      goal,
      status: 'running',
      streamStatus: 'connected',
      streamAttempt: 0,
      graphNodes: [],
      subtasks: [],
      thoughtStream: '',
      finalOutput: '',
      errorMessage: '',
      costData: { input_tokens: 0, output_tokens: 0, total_cost: 0 },
      criticScore: null,
      goalAnalysis: null,
      reasoningOutput: null,
      currentMode: mode ?? 'fast',
    }),

  handleEvent: (event: ARIAEvent) => {
    sseParser.handleEvent(event)
  },

  setStreamStatus: (status, attempt) =>
    set({
      streamStatus: status,
      streamAttempt: typeof attempt === 'number' ? attempt : get().streamAttempt,
    }),

  reset: () => set({ ...INITIAL_STATE, runHistory: get().runHistory, memoryChunks: get().memoryChunks }),

  loadHistory: async () => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/runs?limit=20`)
      if (res.ok) {
        const runs: RunHistoryItem[] = await res.json()
        set({ runHistory: runs })
      }
    } catch (e) {
      console.error('Failed to load history runs from backend:', e)
      set({ runHistory: [] })
    }
  },

  loadMemory: async () => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/memory?limit=50`)
      if (res.ok) {
        const data = await res.json()
        set({ memoryChunks: data.memories ?? [] })
      }
    } catch (e) {
      console.error('Failed to load memory chunks from backend:', e)
      set({ memoryChunks: [] })
    }
  },

  pauseRun: async () => {
    const { runId } = get()
    if (!runId) return
    try {
      await fetch(`${API_BASE}/api/v1/runs/${runId}/pause`, { method: 'POST' })
    } catch (e) { }
  },

  resumeRun: async (directive?: string) => {
    const { runId } = get()
    if (!runId) return
    try {
      await fetch(`${API_BASE}/api/v1/runs/${runId}/resume`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ directive }),
      })
    } catch (e) { }
  },

  abortRun: async () => {
    const { runId } = get()
    if (!runId) return
    try {
      await fetch(`${API_BASE}/api/v1/runs/${runId}/abort`, { method: 'POST' })
    } catch (e) { }
  },

  deleteRun: async (runId: string) => {
    try {
      await fetch(`${API_BASE}/api/v1/runs/${runId}`, { method: 'DELETE' })
      set((s) => ({
        runHistory: s.runHistory.filter((r) => r.run_id !== runId),
      }))
    } catch (e) { }
  },

  viewHistoryRun: async (run: RunHistoryItem) => {
    // 1. Validate and map status
    const validStatuses = ['idle', 'running', 'paused', 'completed', 'error']
    const mappedStatus = run.status === 'pending' ? 'idle' : run.status
    const safeStatus = validStatuses.includes(mappedStatus) ? mappedStatus as RunState['status'] : 'completed'

    // 2. Set initial basic state
    set({
      runId: run.run_id,
      goal: run.goal,
      status: safeStatus,
      finalOutput: run.output ?? '',
      graphNodes: [],
      subtasks: [],
      thoughtStream: '',
      criticScore: null,
      reasoningOutput: null,
    })

    // 2. Fetch events to reconstruct graph/subtasks
    try {
      const res = await fetch(`${API_BASE}/api/v1/runs/${run.run_id}/events`)
      if (res.ok) {
        const events = await res.json()
        // Sort events by created_at just in case
        events.sort((a: any, b: any) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime())

        // 3. Replay events through handleEvent
        for (const eventWrapper of events) {
          try {
            const payload = JSON.parse(eventWrapper.payload)
            get().handleEvent(payload)
          } catch (e) {
            console.warn('Failed to parse event payload', e)
          }
        }
      }
    } catch (e) {
      console.error('Failed to load history events', e)
    }
  },
}))
