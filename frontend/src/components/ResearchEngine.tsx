import { useARIAStore } from '../store'
import { CheckCircle, Globe, Activity, Layers, Wrench, Database, ListTodo, User, Settings, Sparkles, FileText, Microscope } from 'lucide-react'
import { useMemo } from 'react'

const DEFAULT_NODES = [
    { id: 'intake', label: 'Goal Intake', icon: User },
    { id: 'planning', label: 'Planning', icon: ListTodo },
    { id: 'research', label: 'Research', icon: Globe },
    { id: 'analysis', label: 'Deep Analysis', icon: Activity },
    { id: 'reasoning', label: 'Reasoning', icon: Sparkles },
    { id: 'synthesis', label: 'Synthesis', icon: Layers },
    { id: 'review', label: 'Review', icon: Microscope },
    { id: 'memory', label: 'Persistence', icon: Database },
]

function getStatusInfo(status: string) {
    if (status === 'running') return { text: 'Active', bg: 'bg-blue-50', fg: 'text-blue-600', color: '#3B82F6' }
    if (status === 'done') return { text: 'Done', bg: 'bg-emerald-50', fg: 'text-emerald-600', color: '#22C55E' }
    if (status === 'error' || status === 'failed') return { text: 'Error', bg: 'bg-red-50', fg: 'text-red-500', color: '#EF4444' }
    return { text: 'Pending', bg: 'bg-slate-100', fg: 'text-slate-400', color: '#94A3B8' }
}

export function ResearchEngine() {
    const { graphNodes, status: runStatus, currentMode } = useARIAStore()

    const isDeep = currentMode === 'deep'

    // Build the display nodes from static list, merging in status from real graph state
    const displayNodes = DEFAULT_NODES.map(node => {
        const liveNode = graphNodes.find(n => n.id === node.id)
        return {
            ...node,
            status: liveNode ? liveNode.status : 'idle' as const
        }
    })

    const nodeCount = displayNodes.length
    const baseRadius = 210

    const isRunning = runStatus === 'running'

    const activeIndex = useMemo(() => {
        const runningIdx = displayNodes.findIndex((n) => n.status === 'running')
        if (runningIdx >= 0) return runningIdx
        // fall back to last done
        let lastDone = -1
        displayNodes.forEach((n, i) => {
            if (n.status === 'done') lastDone = i
        })
        return Math.max(lastDone, 0)
    }, [displayNodes])

    return (
        <div className="re-container">
            {/* Section Title */}
            <div className="re-title">
                <div className="re-title-line" />
                <span>RESEARCH PIPELINE</span>
                {isDeep && (
                    <span className="ml-2 px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-purple-100 text-purple-700 animate-pulse">
                        Deep
                    </span>
                )}
                {!isDeep && (
                    <span className="ml-2 px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-blue-100 text-blue-600">
                        Standard
                    </span>
                )}
                <div className="re-title-line" />
            </div>

            {/* Orbital Area */}
            <div className="re-orbital">
                {/* Outer ring */}
                <div className="re-ring re-ring-outer" />
                {/* Inner ring */}
                <div className="re-ring re-ring-inner" />
                {/* Decorative dashed ring */}
                <div className={`re-ring re-ring-dashed ${isRunning ? 'spinning' : ''}`} />

                {/* Flow dot that moves to the active stage */}
                <div
                    className={`re-flow-dot ${isRunning ? 'active' : ''}`}
                    style={{
                        // map node index to angle, matching the node placement logic
                        transform: `rotate(${(360 * activeIndex) / nodeCount - 90}deg) translateY(-${baseRadius + 6}px)`,
                    }}
                />

                {/* Connector accent marks on the ring */}
                {[0, 45, 90, 135, 180, 225, 270, 315].map((deg) => (
                    <div
                        key={deg}
                        className="re-ring-tick"
                        style={{
                            transform: `rotate(${deg}deg) translateY(-${baseRadius + 12}px)`,
                        }}
                    />
                ))}

                {/* Center Orb */}
                <div className="re-center-orb">
                    <div className={`re-orb-glow ${isRunning ? 'active' : ''} ${isDeep ? 'deep-mode' : ''}`} />
                    <div className="re-orb-inner">
                        <div className="re-orb-globe" />
                    </div>
                    <div className="re-orb-label">
                        <span className="re-orb-name">ARIA CORE</span>
                        <span className="re-orb-sub">Advanced Research Engine</span>
                        <span className="re-orb-status">
                            Status: <span className="re-orb-status-val">{isRunning ? 'Running' : runStatus === 'completed' ? 'Complete' : 'Idle'}</span>
                        </span>
                    </div>
                </div>

                {/* Pipeline Nodes arranged in circle */}
                {displayNodes.map((node, i) => {
                    const angle = (2 * Math.PI * i) / nodeCount - Math.PI / 2
                    const x = Math.cos(angle) * baseRadius
                    const y = Math.sin(angle) * baseRadius
                    const info = getStatusInfo(node.status)
                    const NodeIcon = node.icon
                    const isActive = node.status === 'running' || node.status === 'done'
                    const showBadge = node.status === 'running' || node.status === 'done' || node.status === 'error'
                    const isCurrentStep = i === activeIndex

                    return (
                        <div key={node.id}>
                            <div
                                className={`re-node ${node.status === 'running' ? 'floating' : ''} ${!isActive ? 're-node-muted' : ''}`}
                                style={{
                                    transform: `translate(${x}px, ${y}px)`,
                                }}
                            >
                                <div className="re-node-inner" style={{ animationDelay: `${i * 0.15}s` }}>
                                    <div
                                        className={`re-node-icon ${isActive ? 'active' : ''} ${node.status === 'running' ? 'pulsing' : ''}`}
                                        style={isActive ? { background: info.color, borderColor: 'transparent' } : {}}
                                    >
                                        <NodeIcon size={18} strokeWidth={2.2} className={isActive ? 'text-white' : 'text-slate-400'} />
                                    </div>
                                    <div className="re-node-info">
                                        <span className="re-node-label">{node.label}</span>
                                        {showBadge && <span className={`re-node-badge ${info.bg} ${info.fg}`}>{info.text}</span>}
                                    </div>
                                </div>
                            </div>

                            {/* Directional Arrow – only show for the current active step */}
                            {isRunning && isCurrentStep && (
                                <div
                                    className="absolute left-1/2 top-1/2 w-[500px] h-[500px] -ml-[250px] -mt-[250px] pointer-events-none opacity-100 transition-opacity duration-700"
                                    style={{ transform: `rotate(${(angle * 180 / Math.PI) + 90}deg)` }}
                                >
                                    <svg width="100%" height="100%" viewBox="-250 -250 500 500" className="absolute inset-0">
                                        <path
                                            d={`M ${Math.cos(-Math.PI / 2 + 0.3) * baseRadius} ${Math.sin(-Math.PI / 2 + 0.3) * baseRadius} A ${baseRadius} ${baseRadius} 0 0 1 ${Math.cos(-Math.PI / 2 + (2 * Math.PI / nodeCount) - 0.3) * baseRadius} ${Math.sin(-Math.PI / 2 + (2 * Math.PI / nodeCount) - 0.3) * baseRadius}`}
                                            fill="none"
                                            stroke="#3B82F6"
                                            strokeWidth="2"
                                            strokeDasharray="4 4"
                                            className="animate-dash-flow"
                                        />
                                        <polygon
                                            points="0,-4 -4,4 4,4"
                                            fill="#3B82F6"
                                            transform={`translate(${Math.cos(-Math.PI / 2 + (2 * Math.PI / nodeCount) - 0.3) * baseRadius}, ${Math.sin(-Math.PI / 2 + (2 * Math.PI / nodeCount) - 0.3) * baseRadius}) rotate(${(2 * Math.PI / nodeCount) * 180 / Math.PI}) scale(1.5)`}
                                        />
                                    </svg>
                                </div>
                            )}
                        </div>
                    )
                })}
            </div>
        </div>
    )
}
