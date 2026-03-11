import { useARIAStore } from '../store'
import { FileText, Search, Activity, Layers, Cpu, Terminal, ChevronRight, ChevronLeft, User, Database, Settings, PauseCircle, PlayCircle, StopCircle, Sparkles, BarChart2, ShieldCheck, Microscope, RefreshCw, Network, Lightbulb, MessageSquare, Globe } from 'lucide-react'
import { useRef, useEffect, useState } from 'react'
import React from 'react'
import { useRunStream } from '../hooks/useRunStream'

export function RightSidebar() {
    const { status: overallStatus, graphNodes, thoughtStream, costData, pauseRun, resumeRun, abortRun, streamStatus, streamAttempt } = useARIAStore()
    const { retryStream } = useRunStream()
    const bottomRef = useRef<HTMLDivElement>(null)
    const [isOpen, setIsOpen] = useState(true)
    const [isControlBusy, setIsControlBusy] = useState(false)
    const [confirmStopOpen, setConfirmStopOpen] = useState(false)

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, [thoughtStream])

    const formatStatus = (st: string) => {
        if (st === 'running') return 'In Progress'
        if (st === 'done') return 'Completed'
        if (st === 'error') return 'Failed'
        return 'Pending'
    }

    const getIconForNode = (id: string) => {
        if (id === 'goal_understanding') return <User size={16} />
        if (id === 'query_understanding') return <Search size={16} />
        if (id === 'planner') return <FileText size={16} />
        if (id === 'strategy_generator') return <BarChart2 size={16} />
        if (id === 'source_discovery') return <Globe size={16} />
        if (id.startsWith('subtask_')) return <Search size={16} />
        if (id === 'source_validator') return <ShieldCheck size={16} />
        if (id === 'evidence_extractor') return <Microscope size={16} />
        if (id === 'normalizer') return <RefreshCw size={16} />
        if (id === 'kg_builder') return <Network size={16} />
        if (id === 'hypothesis_generator') return <Lightbulb size={16} />
        if (id === 'debate_system') return <MessageSquare size={16} />
        if (id === 'contradiction_detection') return <Activity size={16} />
        if (id === 'insight_synthesis') return <Sparkles size={16} />
        if (id === 'memory') return <Database size={16} />
        if (id === 'reasoning') return <Activity size={16} />
        if (id === 'synthesizer') return <Layers size={16} />
        if (id === 'critic') return <Settings size={16} />
        if (id === 'refiner') return <PauseCircle size={16} />
        return <Cpu size={16} />
    }

    const totalTokens = (costData?.input_tokens || 0) + (costData?.output_tokens || 0)
    const hasBackendCost = typeof costData?.total_cost === 'number' && costData.total_cost > 0
    const showReconnectBanner = (overallStatus === 'running' || overallStatus === 'paused') && (streamStatus === 'reconnecting' || streamStatus === 'disconnected')

    return (
        <div className={`shrink-0 hidden lg:flex flex-col gap-4 p-4 pl-6 h-full bg-[#f8fafc] border-l border-slate-200 relative transition-all duration-300 ease-in-out ${isOpen ? 'w-[340px]' : 'w-[20px] px-0 pl-2 py-0'}`}>
            {/* Toggle Button */}
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="absolute -left-4 top-1/2 -translate-y-1/2 w-8 h-12 bg-white border border-slate-200 shadow-sm rounded-l-xl flex items-center justify-center text-slate-400 hover:text-blue-600 transition-colors z-50 hover:bg-slate-50"
                title={isOpen ? "Collapse Sidebar" : "Expand Sidebar"}
            >
                {isOpen ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
            </button>

            {isOpen && (
                <>
                    <div className="bg-white rounded-2xl p-4 shadow-[0_2px_12px_rgba(0,0,0,0.03)] border border-slate-200/60 shrink-0 max-h-[55vh] overflow-y-auto custom-scrollbar flex flex-col gap-2.5">
                        {/* Header Area */}
                        <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                            <div className="flex items-center gap-2.5">
                                <div className={`relative flex items-center justify-center w-6 h-6 rounded-md ${overallStatus === 'running' ? 'bg-blue-100 text-blue-600' : 'bg-slate-100 text-slate-500'}`}>
                                    {overallStatus === 'running' && <div className="absolute inset-0 bg-blue-400 opacity-20 animate-ping rounded-md" />}
                                    <Activity size={14} className={overallStatus === 'running' ? 'animate-pulse' : ''} />
                                </div>
                                <h3 className="text-sm text-slate-800 font-semibold tracking-tight">Research Activity</h3>
                            </div>
                        </div>

                        {showReconnectBanner && (
                            <div className={`rounded-xl border px-3 py-2 text-[12px] font-medium flex items-center justify-between gap-3 ${streamStatus === 'disconnected' ? 'bg-red-50 border-red-100 text-red-700' : 'bg-amber-50 border-amber-100 text-amber-800'}`}>
                                <div className="min-w-0">
                                    <p className="truncate">
                                        {streamStatus === 'disconnected'
                                            ? 'Disconnected from server.'
                                            : `Reconnecting… (attempt ${Math.max(streamAttempt, 1)})`}
                                    </p>
                                </div>
                                <button
                                    type="button"
                                    onClick={() => retryStream()}
                                    disabled={isControlBusy}
                                    className="shrink-0 px-2.5 py-1 rounded-lg bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 disabled:opacity-50 disabled:cursor-not-allowed"
                                    title="Retry stream connection"
                                >
                                    Retry
                                </button>
                            </div>
                        )}

                        {/* Controls & Metrics */}
                        {overallStatus !== 'idle' && (
                            <div className="flex flex-col gap-3">
                                <div className="bg-slate-50 p-3 rounded-xl border border-slate-100 space-y-2">
                                    <div className="flex justify-between items-center">
                                        <div className="flex flex-col">
                                            <span className="text-[10px] text-slate-400 font-semibold uppercase tracking-wider mb-0.5">Total Tokens</span>
                                            <span className="text-sm font-bold text-slate-700 font-mono">
                                                {totalTokens.toLocaleString()}
                                            </span>
                                        </div>
                                        <div className="flex flex-col text-right">
                                            <span className="text-[10px] text-emerald-600/70 font-semibold uppercase tracking-wider mb-0.5">
                                                {hasBackendCost ? 'Total Cost' : 'Est. Cost'}
                                            </span>
                                            <span className="text-sm font-bold text-emerald-600 font-mono">
                                                ${(hasBackendCost ? costData!.total_cost : totalTokens * 0.00005).toFixed(4)}
                                            </span>
                                        </div>
                                    </div>

                                    <div className="grid grid-cols-2 gap-2 pt-2 border-t border-slate-100">
                                        <div className="flex flex-col">
                                            <span className="text-[10px] text-slate-400 font-semibold uppercase tracking-wider mb-0.5">Input</span>
                                            <span className="text-[12px] font-bold text-slate-600 font-mono">
                                                {(costData?.input_tokens || 0).toLocaleString()}
                                            </span>
                                        </div>
                                        <div className="flex flex-col text-right">
                                            <span className="text-[10px] text-slate-400 font-semibold uppercase tracking-wider mb-0.5">Output</span>
                                            <span className="text-[12px] font-bold text-slate-600 font-mono">
                                                {(costData?.output_tokens || 0).toLocaleString()}
                                            </span>
                                        </div>
                                    </div>
                                </div>

                                {(overallStatus === 'running' || overallStatus === 'paused') && (
                                    <div className="flex gap-2.5">
                                        {overallStatus === 'running' ? (
                                            <button
                                                onClick={async () => { setIsControlBusy(true); try { await pauseRun() } finally { setIsControlBusy(false) } }}
                                                disabled={isControlBusy}
                                                className="flex-1 flex items-center justify-center gap-2 bg-amber-50 hover:bg-amber-100 text-amber-600 border border-amber-200/50 font-medium text-xs py-2 rounded-xl transition-all shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
                                            >
                                                <PauseCircle size={14} /> Pause
                                            </button>
                                        ) : (
                                            <button
                                                onClick={async () => { setIsControlBusy(true); try { await resumeRun() } finally { setIsControlBusy(false) } }}
                                                disabled={isControlBusy}
                                                className="flex-1 flex items-center justify-center gap-2 bg-emerald-50 hover:bg-emerald-100 text-emerald-600 border border-emerald-200/50 font-medium text-xs py-2 rounded-xl transition-all shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
                                            >
                                                <PlayCircle size={14} /> Resume
                                            </button>
                                        )}
                                        <button
                                            onClick={() => setConfirmStopOpen(true)}
                                            disabled={isControlBusy}
                                            className="flex-1 flex items-center justify-center gap-2 bg-red-50 hover:bg-red-100 text-red-600 border border-red-200/50 font-medium text-xs py-2 rounded-xl transition-all shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
                                        >
                                            <StopCircle size={14} /> Stop
                                        </button>
                                    </div>
                                )}
                            </div>
                        )}

                        {/* Node List */}
                        <div className="flex flex-col gap-2 relative">
                            {graphNodes.length === 0 ? (
                                <div className="text-center text-xs text-slate-400 py-6">Waiting for agent to initialize...</div>
                            ) : graphNodes.map((node, index) => {
                                const isRunning = node.status === 'running'
                                const isDone = node.status === 'done'
                                const isPending = node.status === 'idle'

                                return (
                                    <div key={node.id} className="relative flex items-center gap-3 group py-1">

                                        {/* Icon */}
                                        <div className={`relative z-10 w-8 h-8 rounded-full flex items-center justify-center shrink-0 transition-all duration-300 shadow-sm border ${isRunning ? 'bg-blue-600 text-white border-blue-600 ring-4 ring-blue-50' :
                                            isDone ? 'bg-white text-emerald-500 border-emerald-200' :
                                                'bg-white text-slate-300 border-slate-200'
                                            }`}>
                                            {getIconForNode(node.id)}
                                        </div>

                                        {/* Content */}
                                        <div className={`flex-1 min-w-0 pb-1 ${isPending ? 'opacity-50' : 'opacity-100'}`}>
                                            <div className="flex items-center justify-between">
                                                <p className={`text-[13px] font-semibold truncate capitalize transition-colors ${isRunning ? 'text-blue-900' : isDone ? 'text-slate-700' : 'text-slate-500'}`}>
                                                    {node.label}
                                                </p>
                                                <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium tracking-wide ${isRunning ? 'bg-blue-50 text-blue-600 animate-pulse' :
                                                    isDone ? 'bg-emerald-50 text-emerald-600' :
                                                        'text-slate-400'
                                                    }`}>
                                                    {formatStatus(node.status)}
                                                </span>
                                            </div>
                                        </div>
                                    </div>
                                )
                            })}
                        </div>
                    </div>

                    {/* Agent Thinking Panel */}
                    {(overallStatus === 'running' || thoughtStream) && (
                        <div className="bg-[#0f1117] rounded-2xl shadow-[0_4px_24px_rgba(0,0,0,0.15)] border border-[#1e2330] flex-1 flex flex-col min-h-0 overflow-hidden relative group">
                            <div className="flex items-center justify-between px-4 py-3 shrink-0 bg-[#161922] border-b border-[#1e2330]">
                                <div className="flex items-center gap-2">
                                    <Terminal size={14} className="text-[#38BDF8]" />
                                    <h3 className="text-[11px] text-slate-300 font-bold uppercase tracking-widest textShadow-sm">Agent Thinking</h3>
                                </div>
                                {overallStatus === 'running' && (
                                    <div className="flex items-center gap-1.5">
                                        <span className="w-2 h-2 rounded-full bg-blue-500 animate-pulse"></span>
                                        <span className="text-[9px] text-blue-400 uppercase tracking-widest font-semibold">Active</span>
                                    </div>
                                )}
                            </div>

                            <div className="flex-1 overflow-y-auto p-4 font-mono text-[12px] text-slate-400 leading-relaxed custom-scrollbar">
                                {thoughtStream ? (
                                    thoughtStream.trim().split('\n').filter(Boolean).map((line, i) => {
                                        let content: React.ReactNode = line;

                                        // Syntax Highlighting for the terminal output
                                        if (line.includes('Confidence:')) {
                                            const parts = line.split('Confidence:');
                                            content = <>{parts[0]}<span className="text-emerald-400 font-semibold">Confidence:</span>{parts[1]}</>;
                                        } else if (line.includes('Patterns:')) {
                                            const parts = line.split('Patterns:');
                                            content = <>{parts[0]}<span className="text-blue-400 font-semibold">Patterns:</span>{parts[1]}</>;
                                        } else if (line.includes('Contradictions:')) {
                                            const parts = line.split('Contradictions:');
                                            content = <>{parts[0]}<span className="text-rose-400 font-semibold">Contradictions:</span>{parts[1]}</>;
                                        } else if (line.includes('Conclusions:')) {
                                            const parts = line.split('Conclusions:');
                                            content = <>{parts[0]}<span className="text-purple-400 font-semibold">Conclusions:</span>{parts[1]}</>;
                                        } else if (line.includes('Gaps:')) {
                                            const parts = line.split('Gaps:');
                                            content = <>{parts[0]}<span className="text-amber-400 font-semibold">Gaps:</span>{parts[1]}</>;
                                        } else {
                                            // Handle [bracket] tags like [reasoning] or [synthesizer]
                                            const bracketMatch = line.match(/^(\[[^\]]+\])(.*)/);
                                            if (bracketMatch) {
                                                content = <><span className="text-[#38BDF8] opacity-80">{bracketMatch[1]}</span><span className="text-slate-300">{bracketMatch[2]}</span></>;
                                            }
                                        }

                                        return (
                                            <div key={i} className="mb-2 break-words flex gap-2 hover:bg-[#1a1e29] px-1 -mx-1 rounded transition-colors duration-150">
                                                <span className="text-slate-600 select-none opacity-50">›</span>
                                                <span className="flex-1">{content}</span>
                                            </div>
                                        )
                                    })
                                ) : (
                                    <div className="text-slate-600 italic flex items-center gap-2">
                                        <div className="w-1.5 h-1.5 bg-slate-600 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                                        <div className="w-1.5 h-1.5 bg-slate-600 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                                        <div className="w-1.5 h-1.5 bg-slate-600 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                                        <span className="ml-2 text-xs">Awaiting task initialization...</span>
                                    </div>
                                )}
                                {overallStatus === 'running' && (
                                    <span className="inline-block w-2 h-4 bg-[#38BDF8] animate-pulse ml-4 align-middle rounded-sm mt-1" />
                                )}
                                <div ref={bottomRef} className="h-4" />
                            </div>
                        </div>
                    )}
                </>
            )}

            {/* Confirm Stop Modal */}
            {confirmStopOpen && (
                <div className="absolute inset-0 z-[200] flex items-center justify-center px-4">
                    <div className="absolute inset-0 bg-slate-900/20 backdrop-blur-[1px]" onClick={() => !isControlBusy && setConfirmStopOpen(false)} />
                    <div className="relative w-full max-w-[320px] rounded-2xl bg-white border border-slate-200 shadow-[0_10px_40px_rgba(0,0,0,0.15)] p-4">
                        <h4 className="text-sm font-semibold text-slate-800">Stop this research run?</h4>
                        <p className="text-xs text-slate-500 mt-1.5 leading-relaxed">
                            This will abort the current run. You can start a new one anytime.
                        </p>
                        <div className="mt-4 flex gap-2">
                            <button
                                type="button"
                                onClick={() => setConfirmStopOpen(false)}
                                disabled={isControlBusy}
                                className="flex-1 px-3 py-2 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-xs font-semibold disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                Cancel
                            </button>
                            <button
                                type="button"
                                onClick={async () => {
                                    setIsControlBusy(true)
                                    try { await abortRun() } finally { setIsControlBusy(false); setConfirmStopOpen(false) }
                                }}
                                disabled={isControlBusy}
                                className="flex-1 px-3 py-2 rounded-xl bg-red-600 hover:bg-red-700 text-white text-xs font-semibold disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                Stop run
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}

