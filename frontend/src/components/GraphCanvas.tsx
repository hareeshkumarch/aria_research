import React from 'react'
import { useARIAStore } from '../store'
import { User, ListTodo, Globe, Activity, Layers, FileText, Database, Settings, Sparkles, Search, ShieldCheck, Microscope, RefreshCw, Network, Lightbulb, MessageSquare, BarChart2 } from 'lucide-react'

// ─── Pipeline Node Types & Config ───────────────────────────────────────────

function getIconForNode(nodeId: string) {
  if (nodeId === 'goal_understanding') return User
  if (nodeId === 'query_understanding') return Search
  if (nodeId === 'planner') return ListTodo
  if (nodeId === 'strategy_generator') return BarChart2
  if (nodeId === 'source_discovery') return Globe
  if (nodeId.startsWith('subtask_')) return Search
  if (nodeId === 'source_validator') return ShieldCheck
  if (nodeId === 'evidence_extractor') return Microscope
  if (nodeId === 'normalizer') return RefreshCw
  if (nodeId === 'kg_builder') return Network
  if (nodeId === 'hypothesis_generator') return Lightbulb
  if (nodeId === 'debate_system') return MessageSquare
  if (nodeId === 'contradiction_detection') return Activity
  if (nodeId === 'insight_synthesis') return Sparkles
  if (nodeId === 'memory') return Database
  if (nodeId === 'reasoning') return Activity
  if (nodeId === 'synthesizer') return Layers
  if (nodeId === 'critic') return Settings
  if (nodeId === 'refiner') return Sparkles
  return FileText // fallback
}

// ─── Single Pipeline Node ───────────────────────────────────────────────────

function PipelineNode({ config, status, isLast }: {
  config: { key: string; label: string; icon: any };
  status: 'idle' | 'running' | 'done' | 'failed';
  isLast?: boolean;
}) {
  const isRunning = status === 'running'
  const isDone = status === 'done'
  const isPending = status === 'idle'

  return (
    <div className="flex flex-col items-center gap-3 relative min-w-[110px] sm:min-w-[120px] group select-none">
      {/* Node Circle */}
      <div className="relative flex items-center justify-center">
        {isRunning && (
          <div className="absolute inset-0 rounded-full bg-blue-400 opacity-20 animate-[ping_2s_cubic-bezier(0,0,0.2,1)_infinite] z-0 scale-150" />
        )}
        <div
          className={`relative z-10 w-10 h-10 md:w-12 md:h-12 rounded-full flex items-center justify-center transition-all duration-500 shadow-sm ${isDone
            ? 'bg-gradient-to-br from-emerald-400 to-emerald-500 text-white border-2 border-white/50 shadow-emerald-500/20'
            : isRunning
              ? 'bg-gradient-to-br from-blue-500 to-indigo-600 text-white border-2 border-white/50 shadow-blue-500/30 scale-110 ring-4 ring-blue-50'
              : 'bg-white border border-slate-200 text-slate-400 hover:border-slate-300 shadow-sm'
            }`}
        >
          <config.icon size={18} className={isPending ? 'text-slate-400 transition-colors group-hover:text-slate-500' : 'text-white'} strokeWidth={isDone || isRunning ? 2.5 : 2} />
        </div>
      </div>

      {/* Label & Status */}
      <div className="flex flex-col items-center gap-1 mt-0.5">
        <span className={`text-[10px] md:text-[11px] font-semibold tracking-tight transition-colors duration-300 text-center whitespace-nowrap ${isRunning ? 'text-blue-900' : isDone ? 'text-slate-800' : 'text-slate-500'
          }`}>
          {config.label}
        </span>
        <span className={`text-[9px] px-2 py-0.5 rounded-full capitalize font-semibold tracking-wide ${isRunning ? 'bg-blue-50 text-blue-600 animate-pulse' :
          isDone ? 'bg-emerald-50 text-emerald-600' :
            'bg-slate-100 text-slate-400'
          }`}>
          {status === 'idle' ? 'Pending' : status === 'running' ? 'Active' : status}
        </span>
      </div>
    </div>
  )
}

function FlowConnector({ isActive, isFlowing }: { isActive: boolean; isFlowing: boolean }) {
  return (
    <div className="flex-1 w-full min-w-[30px] max-w-[90px] flex items-center justify-center relative -mt-10 mx-1">
      <div className={`h-[3px] w-full transition-all duration-700 relative overflow-hidden rounded-full ${isActive ? 'bg-blue-100' : 'bg-slate-100'}`}>
        {isActive && !isFlowing && (
          <div className="absolute inset-0 bg-emerald-400" />
        )}
        {isFlowing && (
          <div className="absolute inset-0 bg-blue-500">
            <div className="absolute top-0 left-0 h-full w-[40%] bg-white/60 blur-[2px] animate-[flow_1.5s_ease-in-out_infinite]" />
          </div>
        )}
      </div>
    </div>
  )
}

export function GraphCanvas() {
  const { graphNodes } = useARIAStore()

  return (
    <div className="w-full bg-white rounded-2xl shadow-[0_2px_12px_rgba(0,0,0,0.03)] border border-slate-200/60 flex flex-col relative overflow-hidden">
      {/* Background Decor */}
      <div className="absolute top-0 left-0 w-full h-[120px] bg-gradient-to-b from-slate-50/50 to-white z-0 pointer-events-none" />

      <div className="px-6 py-4 flex items-center gap-2 border-b border-slate-100 relative z-10 w-full bg-white/50 backdrop-blur-sm">
        <Layers size={16} className="text-slate-400" />
        <h3 className="text-[12px] font-bold text-slate-700 uppercase tracking-widest">Research Pipeline</h3>
      </div>

      <div className="flex flex-wrap items-center justify-center w-full px-4 py-6 relative z-10 mx-auto gap-y-8 gap-x-0">
        {graphNodes.length === 0 ? (
          <div className="flex flex-col items-center justify-center text-slate-400 gap-3 animate-fade-in py-6">
            <div className="w-12 h-12 rounded-2xl bg-slate-50 border border-slate-100 flex items-center justify-center shadow-sm">
              <Activity size={20} className="text-slate-400/70" />
            </div>
            <span className="text-[13px] font-medium tracking-wide text-slate-500">Awaiting initialization sequence...</span>
          </div>
        ) : (
          graphNodes.map((node, i) => {
            const isActive = node.status === 'done' || node.status === 'running'
            const isFlowing = i > 0 && graphNodes[i - 1].status === 'done' && node.status === 'running'
            const Icon = getIconForNode(node.id)

            return (
              <React.Fragment key={node.id}>
                {i > 0 && (
                  <FlowConnector
                    isActive={isActive}
                    isFlowing={isFlowing}
                  />
                )}
                <div className="flex items-center">
                  <PipelineNode config={{ key: node.id, label: node.label, icon: Icon } as any} status={node.status as any} isLast={i === graphNodes.length - 1} />
                </div>
              </React.Fragment>
            )
          })
        )}
      </div>
    </div>
  )
}
