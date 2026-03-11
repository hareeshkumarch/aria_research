import { useARIAStore } from '../store'
import type { ARIAEvent, CriticScore } from '../types'

/**
 * Service to process incoming SSE events and dispatch them to the Zustand store.
 * Extracted from store.ts to satisfy Single Responsibility Principle.
 */
export const sseParser = {
    handleEvent: (event: ARIAEvent) => {
        const store = useARIAStore.getState()

        switch (event.type) {
            case 'run_start': {
                useARIAStore.setState({
                    graphNodes: [
                        { id: 'goal_understanding', label: '🎯 Goal Understanding', status: 'idle', type: 'goal_understanding' },
                    ],
                })
                break
            }

            case 'goal_understood': {
                const analysis = event.analysis ?? null
                const s = useARIAStore.getState()
                useARIAStore.setState({
                    goalAnalysis: analysis,
                    graphNodes: s.graphNodes.map((n) =>
                        n.id === 'goal_understanding'
                            ? { ...n, status: 'done' as const, duration_ms: event.duration_ms }
                            : n
                    ),
                    thoughtStream: s.thoughtStream +
                        `\n[goal_understanding] Goal analyzed${event.duration_ms ? ` [${event.duration_ms}ms]` : ''}` +
                        (analysis ? `\n  Intent: ${analysis.intent}` +
                            `\n  Entities: ${analysis.key_entities?.join(', ') ?? 'none'}` +
                            `\n  Scope: ${analysis.scope}` +
                            `\n  Expected: ${analysis.expected_output}` : ''),
                })
                break
            }

            case 'node_start': {
                const nodeId = event.node!
                const label = event.label ?? nodeId
                const s = useARIAStore.getState()

                // Mapping for 17-stage visualization
                let targetId = nodeId
                if (nodeId.startsWith('subtask_')) targetId = 'source_discovery'
                if (nodeId === 'reasoning') targetId = 'contradiction_detection'

                // Mapping for 8-node ResearchEngine orbital
                const orbitalMap: Record<string, string> = {
                    'intake': 'intake', 'goal_understanding': 'intake',
                    'planning': 'planning', 'planner': 'planning', 'strategy_generator': 'planning',
                    'research': 'research', 'executor': 'research', 'source_discovery': 'research',
                    'analysis': 'analysis', 'source_validator': 'analysis', 'evidence_extractor': 'analysis',
                    'normalizer': 'analysis', 'kg_builder': 'analysis', 'hypothesis_generator': 'analysis',
                    'debate_system': 'analysis',
                    'reasoning': 'reasoning', 'contradiction_detection': 'reasoning', 'insight_synthesis': 'reasoning',
                    'synthesis': 'synthesis', 'synthesizer': 'synthesis',
                    'review': 'review', 'critic': 'review',
                    'memory': 'memory', 'refiner': 'research',
                }

                const exists = s.graphNodes.find((n) => n.id === targetId)
                const nodeType = _getNodeType(nodeId)

                let updated = exists
                    ? s.graphNodes.map((n) =>
                        n.id === targetId ? { ...n, status: 'running' as const } : n
                    )
                    : [
                        ...s.graphNodes,
                        { id: targetId, label, status: 'running' as const, type: nodeType },
                    ]

                // Also update orbital node if it exists
                const orbitalId = orbitalMap[nodeId]
                if (orbitalId && orbitalId !== targetId) {
                    const orbitalExists = updated.find((n) => n.id === orbitalId)
                    if (orbitalExists) {
                        updated = updated.map((n) =>
                            n.id === orbitalId ? { ...n, status: 'running' as const } : n
                        )
                    } else {
                        updated = [...updated, { id: orbitalId, label, status: 'running' as const, type: nodeType }]
                    }
                }

                useARIAStore.setState({
                    graphNodes: updated,
                    thoughtStream: s.thoughtStream + `\n[${nodeId}] Processing: ${label}`,
                })
                break
            }

            case 'plan_ready': {
                const subtasks = event.subtasks ?? []
                const s = useARIAStore.getState()

                useARIAStore.setState({
                    subtasks,
                    graphNodes: [
                        ...s.graphNodes.map((n) =>
                            n.id === 'goal_understanding' ? { ...n, label: '1. User Intent Interface' } :
                                n.id === 'planner' ? { ...n, label: '3. Goal Decomposition Planner', status: 'done' as const } : n
                        ),
                        { id: 'query_understanding', label: '2. Query Understanding Agent', status: 'done' as const, type: 'agent' as const },
                        { id: 'strategy_generator', label: '4. Research Strategy Generator', status: 'idle' as const, type: 'agent' as const },
                        { id: 'source_discovery', label: '5. Source Discovery Engine', status: 'idle' as const, type: 'subtask' as const },
                        { id: 'source_validator', label: '6. Source Validation & Scoring', status: 'idle' as const, type: 'critic' as const },
                        { id: 'evidence_extractor', label: '7. Evidence Extraction Engine', status: 'idle' as const, type: 'agent' as const },
                        { id: 'normalizer', label: '8. Knowledge Normalization', status: 'idle' as const, type: 'agent' as const },
                        { id: 'kg_builder', label: '9. Knowledge Graph Builder', status: 'idle' as const, type: 'memory' as const },
                        { id: 'hypothesis_generator', label: '10. Hypothesis Generation Agent', status: 'idle' as const, type: 'reasoning' as const },
                        { id: 'debate_system', label: '11. Multi-Agent Debate System', status: 'idle' as const, type: 'agent' as const },
                        { id: 'contradiction_detection', label: '12. Contradiction Detection', status: 'idle' as const, type: 'reasoning' as const },
                        { id: 'refiner', label: '13. Evidence Re-Query Loop', status: 'idle' as const, type: 'refiner' as const },
                        { id: 'insight_synthesis', label: '14. Insight Synthesis Engine', status: 'idle' as const, type: 'reasoning' as const },
                        { id: 'critic', label: '15. Confidence & Uncertainty Audit', status: 'idle' as const, type: 'critic' as const },
                        { id: 'synthesizer', label: '16. Final Report Generator', status: 'idle' as const, type: 'agent' as const },
                        { id: 'memory', label: '17. Memory & Learning System', status: 'idle' as const, type: 'memory' as const },
                    ],
                    thoughtStream:
                        s.thoughtStream +
                        `\n\n[planner] Created ${subtasks.length} subtasks for Stage 5 Discovery.`,
                })
                break
            }

            case 'node_done': {
                const nodeId = event.node!
                const s = useARIAStore.getState()

                let targetId = nodeId
                if (nodeId.startsWith('subtask_') || nodeId === 'executor') targetId = 'source_discovery'
                if (nodeId === 'reasoning') targetId = 'insight_synthesis'

                // Orbital mapping for ResearchEngine
                const orbitalDoneMap: Record<string, string> = {
                    'intake': 'intake', 'goal_understanding': 'intake',
                    'planning': 'planning', 'planner': 'planning',
                    'research': 'research', 'executor': 'research',
                    'analysis': 'analysis',
                    'reasoning': 'reasoning',
                    'synthesis': 'synthesis', 'synthesizer': 'synthesis',
                    'review': 'review', 'critic': 'review',
                    'memory': 'memory',
                }

                let extra = ''
                if (event.score !== undefined) {
                    extra = ` (score: ${event.score}/10)`
                }
                if (event.duration_ms !== undefined) {
                    extra += ` [${event.duration_ms}ms]`
                }

                let updatedNodes = s.graphNodes.map((n) => {
                    if (n.id === targetId) return { ...n, status: 'done' as const, duration_ms: event.duration_ms }
                    // If reasoning is done, contradiction detection is also done
                    if (nodeId === 'reasoning' && n.id === 'contradiction_detection') return { ...n, status: 'done' as const }
                    return n
                })

                // Also mark orbital node as done
                const orbitalDoneId = orbitalDoneMap[nodeId]
                if (orbitalDoneId) {
                    updatedNodes = updatedNodes.map((n) =>
                        n.id === orbitalDoneId ? { ...n, status: 'done' as const, duration_ms: event.duration_ms } : n
                    )
                }

                useARIAStore.setState({
                    graphNodes: updatedNodes,
                    thoughtStream: s.thoughtStream + (extra ? `\n[${nodeId}] Completed${extra}` : ''),
                })
                break
            }

            case 'tool_call': {
                const s = useARIAStore.getState()
                useARIAStore.setState({
                    thoughtStream:
                        s.thoughtStream +
                        `\n  → [${event.tool}] "${event.query}"`,
                })
                break
            }

            case 'tool_retry': {
                const s = useARIAStore.getState()
                useARIAStore.setState({
                    thoughtStream:
                        s.thoughtStream +
                        `\n  ⟳ Retry #${event.attempt}: ${event.reason}`,
                })
                break
            }

            case 'memory_recall':
            case 'memory_store': {
                const s = useARIAStore.getState()
                useARIAStore.setState({
                    thoughtStream:
                        s.thoughtStream +
                        `\n  💾 ${event.message}`,
                })
                break
            }

            case 'reasoning_complete': {
                const reasoning = event.reasoning ?? null
                const s = useARIAStore.getState()
                useARIAStore.setState({
                    reasoningOutput: reasoning,
                    thoughtStream: s.thoughtStream +
                        `\n\n🧪 Reasoning complete${event.duration_ms ? ` [${event.duration_ms}ms]` : ''}` +
                        (reasoning ? `\n  Confidence: ${reasoning.confidence_score}/10` +
                            (reasoning.patterns?.length ? `\n  Patterns: ${reasoning.patterns.length} found` : '') +
                            (reasoning.contradictions?.length ? `\n  ⚠ Contradictions: ${reasoning.contradictions.length} detected` : '') +
                            (reasoning.conclusions?.length ? `\n  Conclusions: ${reasoning.conclusions.length} derived` : '') +
                            (reasoning.gaps?.length ? `\n  Gaps: ${reasoning.gaps.length} identified` : '') : ''),
                })
                break
            }

            case 'critic_score': {
                const criticScore: CriticScore = {
                    overall_score: event.score ?? 0,
                    strengths: event.strengths ?? [],
                    weaknesses: event.weaknesses ?? [],
                    suggestions: event.suggestions ?? '',
                }
                const s = useARIAStore.getState()
                useARIAStore.setState({
                    criticScore,
                    thoughtStream:
                        s.thoughtStream +
                        `\n\n⚖️ Critic score: ${criticScore.overall_score}/10` +
                        (criticScore.strengths.length ? `\n  ✓ ${criticScore.strengths.join(', ')}` : '') +
                        (criticScore.weaknesses.length ? `\n  ✗ ${criticScore.weaknesses.join(', ')}` : ''),
                })
                break
            }

            case 'cost_update': {
                const s = useARIAStore.getState()
                const anyEvt = event as any
                useARIAStore.setState({
                    costData: {
                        ...s.costData,
                        input_tokens: anyEvt.input_tokens ?? s.costData.input_tokens,
                        output_tokens: anyEvt.output_tokens ?? (event as any).tokens ?? s.costData.output_tokens,
                        total_cost: anyEvt.total_cost ?? anyEvt.cost ?? s.costData.total_cost,
                    },
                })
                break
            }

            case 'metrics_update': {
                // Final run metrics (always emitted at the end of the run)
                const s = useARIAStore.getState()
                const anyEvt = event as any
                const totalTokens = anyEvt.total_tokens ?? 0
                // If we only get total tokens, keep a best-effort split (output as total)
                useARIAStore.setState({
                    costData: {
                        ...s.costData,
                        input_tokens: anyEvt.input_tokens ?? s.costData.input_tokens,
                        output_tokens: anyEvt.output_tokens ?? (totalTokens || s.costData.output_tokens),
                        total_cost: anyEvt.total_cost ?? s.costData.total_cost,
                    },
                })
                // Backend emits this after persisting the run row; refresh history now.
                store.loadHistory()
                break
            }

            case 'token': {
                const s = useARIAStore.getState()
                useARIAStore.setState({ finalOutput: s.finalOutput + (event.content ?? '') })
                break
            }

            case 'run_complete': {
                const s = useARIAStore.getState()
                useARIAStore.setState({
                    status: 'completed',
                    costData: event.cost_data ?? s.costData,
                })
                break
            }

            case 'run_paused': {
                useARIAStore.setState({ status: 'paused' })
                break
            }

            case 'run_resumed': {
                const s = useARIAStore.getState()
                useARIAStore.setState({
                    status: 'running',
                    thoughtStream: s.thoughtStream + `\n\n▶ Run resumed${event.directive ? ` — "${event.directive}"` : ''}`,
                })
                break
            }

            case 'run_aborted': {
                useARIAStore.setState({ status: 'error', errorMessage: 'Run aborted by user.' })
                break
            }

            case 'run_error': {
                const s = useARIAStore.getState()
                useARIAStore.setState({
                    status: 'error',
                    errorMessage: event.error ?? 'Unknown error',
                    graphNodes: s.graphNodes.map((n) =>
                        n.status === 'running' || n.status === 'idle' ? { ...n, status: 'error' } : n
                    ),
                })
                break
            }
        }
    }
}

function _getNodeType(nodeId: string): any {
    if (nodeId === 'goal_understanding' || nodeId === 'intake') return 'goal_understanding'
    if (nodeId === 'reasoning') return 'reasoning'
    if (nodeId === 'memory') return 'memory'
    if (nodeId === 'critic' || nodeId === 'review') return 'critic'
    if (nodeId === 'refiner') return 'refiner'
    if (nodeId === 'synthesizer' || nodeId === 'synthesis' || nodeId === 'planner' || nodeId === 'planning' || nodeId === 'strategy_generator') return 'agent'
    if (nodeId.startsWith('subtask_') || nodeId === 'source_discovery' || nodeId === 'research' || nodeId === 'analysis') return 'subtask'
    return 'agent'
}
