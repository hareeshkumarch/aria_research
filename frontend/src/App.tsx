import { useEffect, useState } from 'react'
import { AlertTriangle, RotateCcw } from 'lucide-react'

import { OutputPanel } from './components/OutputPanel'
import { useARIAStore } from './store'
import { Sidebar } from './components/Sidebar'
import { RightSidebar } from './components/RightSidebar'
import { HeroSearch } from './components/HeroSearch'
import { ResearchEngine } from './components/ResearchEngine'

export default function App() {
  const { loadHistory, loadMemory, status, finalOutput, errorMessage, reset } = useARIAStore()
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    loadHistory()
    loadMemory()
  }, [])

  return (
    <div className={`h-screen max-h-screen w-full flex bg-[#F8FAFC] text-slate-800 font-sans font-['Inter'] overflow-hidden`}>

      {/* ZONE 1 - LEFT SIDEBAR */}
      <Sidebar />

      {/* Main Content Area */}
      <div className={`flex-1 flex flex-col h-full min-w-0 ${status === 'idle' ? 'overflow-visible' : 'overflow-y-auto'} [&::-webkit-scrollbar]:hidden [-ms-overflow-style:none] [scrollbar-width:none]`}>

        {/* Center Column Container */}
        <div className={`flex flex-col w-full max-w-[900px] mx-auto p-4 md:p-8 gap-6 ${status === 'idle' || status === 'error' ? 'mt-[60px]' : 'mt-0 md:mt-2'}`}>

          {/* ZONE 2 - MAIN RESEARCH INPUT */}
          {status === 'idle' && (
            <div className="shrink-0 w-full max-w-[750px] sticky top-[60px] z-50">
              <HeroSearch />
            </div>
          )}

          {/* ZONE 3 - RESEARCH ENGINE VISUALIZATION */}
          {(status === 'running' || status === 'paused') && (
            <div className="shrink-0 w-full animate-fade-in">
              <ResearchEngine />
            </div>
          )}

          {/* Dynamic Content (Output) - only shown when agent has results */}
          {finalOutput && status === 'completed' && (
            <div className="flex-1 flex flex-col w-full min-h-[400px]">
              <div className="flex-1 rounded-2xl bg-white border border-slate-200/60 shadow-[0_2px_12px_rgba(0,0,0,0.03)] overflow-hidden flex flex-col">
                <OutputPanel />
              </div>
            </div>
          )}

          {/* ERROR STATE - shown when a run fails */}
          {status === 'error' && (
            <div className="w-full max-w-[650px] mx-auto animate-fade-in">
              <div className="rounded-2xl bg-white border border-red-200/60 shadow-[0_4px_24px_rgba(239,68,68,0.08)] p-8 flex flex-col items-center text-center gap-5">
                {/* Icon */}
                <div className="w-16 h-16 rounded-full bg-gradient-to-br from-red-50 to-orange-50 border border-red-100 flex items-center justify-center">
                  <AlertTriangle size={28} className="text-red-500" />
                </div>

                {/* Title */}
                <div>
                  <h2 className="text-xl font-semibold text-slate-800 mb-2">Research Run Failed</h2>
                  <p className="text-sm text-slate-500 max-w-md">
                    Something went wrong during the research process. This is usually temporary.
                  </p>
                </div>

                {/* Error Details */}
                {errorMessage && (
                  <div className="w-full rounded-xl bg-red-50/60 border border-red-100 px-5 py-4 text-left">
                    <div className="flex items-center justify-between gap-3 mb-1.5">
                      <p className="text-xs font-semibold text-red-400 uppercase tracking-wider">Error Details</p>
                      <button
                        type="button"
                        onClick={async () => {
                          try {
                            await navigator.clipboard.writeText(errorMessage)
                            setCopied(true)
                            setTimeout(() => setCopied(false), 1200)
                          } catch { }
                        }}
                        className="text-[11px] font-semibold text-red-600 hover:text-red-700 hover:underline"
                        title="Copy error details"
                      >
                        {copied ? 'Copied' : 'Copy'}
                      </button>
                    </div>
                    <p className="text-sm text-red-700 leading-relaxed font-mono break-words">
                      {errorMessage}
                    </p>
                  </div>
                )}

                {/* Suggestions */}
                <div className="w-full rounded-xl bg-slate-50 border border-slate-100 px-5 py-4 text-left">
                  <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">What you can do</p>
                  <ul className="text-sm text-slate-600 space-y-1.5">
                    <li className="flex items-start gap-2"><span className="text-blue-500 mt-0.5">•</span> Wait a few minutes and try again (API rate limits reset over time)</li>
                    <li className="flex items-start gap-2"><span className="text-blue-500 mt-0.5">•</span> Try a different LLM provider or model</li>
                    <li className="flex items-start gap-2"><span className="text-blue-500 mt-0.5">•</span> Check your API key and account usage limits</li>
                  </ul>
                </div>

                {/* Action Button */}
                <button
                  onClick={() => reset()}
                  className="mt-2 inline-flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-blue-600 to-blue-500 text-white rounded-xl font-medium text-sm shadow-md shadow-blue-500/20 hover:shadow-lg hover:shadow-blue-500/30 hover:from-blue-700 hover:to-blue-600 transition-all active:scale-[0.98]"
                >
                  <RotateCcw size={16} />
                  Start New Research
                </button>
              </div>
            </div>
          )}

        </div>

      </div>

      {/* ZONE 4 - LIVE AGENT ACTIVITY PANEL */}
      {(status === 'running' || status === 'paused') && (
        <div className="h-full border-l border-slate-200 animate-fade-in shrink-0 bg-[#f8fafc] overflow-hidden">
          <RightSidebar />
        </div>
      )}

    </div>
  )
}
