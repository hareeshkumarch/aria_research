export type NodeStatus = 'idle' | 'running' | 'done' | 'error'

export interface Subtask {
  id: string
  title: string
  query: string
  description?: string
  tool_hint?: string
  status: string
  result?: string | null
  dependencies?: string[]
}

export interface GoalAnalysis {
  intent: string
  key_entities: string[]
  scope: string
  expected_output: string
  constraints: string[]
  ambiguities: string[]
}

export interface ReasoningOutput {
  evidence_summary: string
  patterns: string[]
  contradictions: string[]
  conclusions: string[]
  confidence_score: number
  gaps: string[]
}

export interface ARIAEvent {
  type: string
  node?: string
  label?: string
  subtasks?: Subtask[]
  subtask_id?: string
  content?: string
  output?: string
  error?: string
  tool?: string
  query?: string
  result_preview?: string
  run_id?: string
  goal?: string
  // Cost events
  tokens?: number
  cost_data?: CostData
  // Critic events
  score?: number
  strengths?: string[]
  weaknesses?: string[]
  suggestions?: string
  // Memory events
  count?: number
  message?: string
  // Control events
  directive?: string
  // Tool retry
  attempt?: number
  reason?: string
  duration_ms?: number
  success?: boolean
  // Goal understanding events
  analysis?: GoalAnalysis
  // Reasoning events
  reasoning?: ReasoningOutput
  // Node timing events
  node_timings?: Record<string, number>
}

export interface GraphNode {
  id: string
  label: string
  status: NodeStatus
  type: 'agent' | 'subtask' | 'tool' | 'memory' | 'critic' | 'refiner' | 'reasoning' | 'goal_understanding'
  duration_ms?: number
  reasoning_summary?: string
}

export interface CostData {
  input_tokens: number
  output_tokens: number
  total_cost: number
  provider?: string
  model?: string
  breakdown?: Record<string, { input_tokens: number; output_tokens: number; cost: number }>
}

export interface CriticScore {
  overall_score: number
  strengths: string[]
  weaknesses: string[]
  suggestions: string
}

export interface MemoryChunk {
  id: string
  text: string
  metadata: {
    run_id?: string
    source?: string
    goal?: string
    importance?: number
  }
  relevance?: number
}

export interface RunHistoryItem {
  run_id: string
  goal: string
  status: string
  output?: string | null
  critic_score?: number | null
  input_tokens?: number | null
  output_tokens?: number | null
  total_tokens?: number | null
  total_cost?: number | null
  created_at?: string | null
}

export interface RunState {
  runId: string | null
  goal: string
  status: 'idle' | 'running' | 'paused' | 'completed' | 'error'
  streamStatus: 'idle' | 'connected' | 'reconnecting' | 'disconnected'
  streamAttempt: number
  graphNodes: GraphNode[]
  subtasks: Subtask[]
  thoughtStream: string
  finalOutput: string
  errorMessage: string
  costData: CostData
  criticScore: CriticScore | null
  goalAnalysis: GoalAnalysis | null
  reasoningOutput: ReasoningOutput | null
  runHistory: RunHistoryItem[]
  memoryChunks: MemoryChunk[]
  currentMode: 'fast' | 'deep'
}
