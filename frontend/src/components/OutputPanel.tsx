import { useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { useARIAStore } from '../store'

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''

export function OutputPanel() {
  const { finalOutput, status, goal, runId, criticScore, errorMessage } = useARIAStore()
  const outputRef = useRef<HTMLDivElement>(null)

  const handleCopy = async () => {
    await navigator.clipboard.writeText(finalOutput)
  }

  const handleDownloadMd = () => {
    const blob = new Blob([`# ARIA Research Report\n\n**Goal:** ${goal}\n\n---\n\n${finalOutput}`], {
      type: 'text/markdown',
    })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `aria-report-${Date.now()}.md`
    a.click()
    URL.revokeObjectURL(url)
  }

  const handleDownloadPdf = async () => {
    if (!runId) return
    try {
      const res = await fetch(`${API_BASE}/api/v1/runs/${runId}/export/pdf`)
      if (!res.ok) throw new Error('PDF export failed')
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `aria-report-${runId.slice(0, 8)}.pdf`
      a.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      console.error('PDF export failed:', e)
    }
  }

  const isStreaming = status === 'running' && finalOutput.length > 0
  const isEmpty = !finalOutput

  // Filter out References block per user request
  const displayOutput = finalOutput
    ? finalOutput.split(/\n##\s+(?:References|Sources)\b/i)[0]
    : ''

  return (
    <div className="h-full flex flex-col min-h-0">
      {/* Header */}
      <div className="flex items-center gap-2 px-4 py-3 border-b border-[#F0F2F8] bg-white shrink-0">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#22C55E" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <polyline points="14 2 14 8 20 8" />
          <line x1="16" y1="13" x2="8" y2="13" />
          <line x1="16" y1="17" x2="8" y2="17" />
        </svg>
        <span className="text-sm font-medium text-[#475569]">Research Output</span>
        {isStreaming && (
          <span className="ml-2 text-xs text-[#4A7BF7] animate-pulse">● streaming…</span>
        )}

        {criticScore && (
          <div className={`ml-2 flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full ${criticScore.overall_score >= 7
            ? 'text-green-600 bg-green-50 border border-green-200'
            : criticScore.overall_score >= 5
              ? 'text-amber-600 bg-amber-50 border border-amber-200'
              : 'text-red-600 bg-red-50 border border-red-200'
            }`}>
            Quality: {criticScore.overall_score.toFixed(1)}/10
          </div>
        )}

        {status === 'completed' && finalOutput && (
          <div className="ml-auto flex gap-2">
            <button
              onClick={handleCopy}
              className="flex items-center gap-1 text-xs text-[#64748B] hover:text-[#1E293B] px-2.5 py-1 rounded-lg border border-[#E2E6F0] hover:border-[#4A7BF7] transition-colors"
            >
              <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="9" y="9" width="13" height="13" rx="2" ry="2" /><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
              </svg>
              Copy
            </button>
            <button
              onClick={handleDownloadMd}
              className="flex items-center gap-1 text-xs text-[#64748B] hover:text-[#1E293B] px-2.5 py-1 rounded-lg border border-[#E2E6F0] hover:border-[#4A7BF7] transition-colors"
            >
              <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="7 10 12 15 17 10" /><line x1="12" y1="15" x2="12" y2="3" />
              </svg>
              .md
            </button>
            <button
              onClick={handleDownloadPdf}
              className="flex items-center gap-1 text-xs text-[#64748B] hover:text-[#1E293B] px-2.5 py-1 rounded-lg border border-[#E2E6F0] hover:border-red-300 transition-colors"
            >
              <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="7 10 12 15 17 10" /><line x1="12" y1="15" x2="12" y2="3" />
              </svg>
              .pdf
            </button>
          </div>
        )}
      </div>

      <div
        ref={outputRef}
        className="flex-1 overflow-y-auto px-5 py-4 bg-white min-h-0"
      >
        {isEmpty && status !== 'running' && (
          <div className="flex flex-col items-center justify-center h-full gap-5 text-center px-6">
            {status === 'completed' ? (
              <>
                <div className="w-16 h-16 rounded-2xl bg-green-50 border border-green-200 flex items-center justify-center">
                  <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#22C55E" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                    <polyline points="22 4 12 14.01 9 11.01" />
                  </svg>
                </div>
                <div>
                  <p className="text-[#1E293B] text-sm font-semibold mb-1">Research Complete</p>
                  <p className="text-[#94A3B8] text-xs max-w-[280px] mx-auto leading-relaxed">
                    This research was completed but the output wasn't saved. Try researching a new topic below.
                  </p>
                </div>
                <div className="flex flex-wrap gap-2 justify-center mt-2">
                  {['AI agent architectures', 'Quantum computing', 'LLM comparison', 'Multi-agent systems'].map(topic => (
                    <button
                      key={topic}
                      onClick={() => {
                        const store = useARIAStore.getState()
                        store.reset()
                        store.setGoal(topic)
                      }}
                      className="px-3.5 py-2 rounded-xl border border-[#E2E6F0] bg-[#F8F9FC] text-xs text-[#475569] hover:text-[#4A7BF7] hover:border-[#4A7BF7] transition-all hover:shadow-sm"
                    >
                      {topic}
                    </button>
                  ))}
                </div>
              </>
            ) : status === 'error' ? (
              <>
                <div className="w-16 h-16 rounded-2xl bg-red-50 border border-red-200 flex items-center justify-center">
                  <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#EF4444" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="12" cy="12" r="10"></circle>
                    <line x1="12" y1="8" x2="12" y2="12"></line>
                    <line x1="12" y1="16" x2="12.01" y2="16"></line>
                  </svg>
                </div>
                <div className="flex flex-col items-center">
                  <p className="text-red-600 text-sm font-semibold mb-1">Research Failed</p>
                  <div className="bg-white/80 rounded-lg p-3 max-w-[400px] w-full mt-2 border border-red-100 shadow-sm">
                    <p className="text-slate-600 text-xs text-left leading-relaxed font-mono break-words line-clamp-4">
                      {errorMessage || "An unexpected error occurred during execution."}
                    </p>
                  </div>
                </div>
              </>
            ) : (
              <>
                <div className="w-16 h-16 rounded-2xl bg-[#F8F9FC] border border-[#E2E6F0] flex items-center justify-center">
                  <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#CBD5E1" strokeWidth="1.5">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                    <polyline points="14 2 14 8 20 8" />
                  </svg>
                </div>
                <div>
                  <p className="text-[#475569] text-sm font-medium mb-1">No Output Generated</p>
                  <p className="text-[#94A3B8] text-xs max-w-[240px] mx-auto leading-relaxed">
                    ARIA's research report will appear here once the agent finishes.
                  </p>
                </div>
              </>
            )}
          </div>
        )}

        {isEmpty && status === 'running' && (
          <div className="flex flex-col items-center justify-center h-full gap-4 text-center">
            <div className="w-16 h-16 rounded-2xl bg-[#EBF0FF] border border-[#4A7BF7]/10 flex items-center justify-center">
              <div className="w-6 h-6 border-2 border-[#4A7BF7]/30 border-t-[#4A7BF7] rounded-full animate-spin" />
            </div>
            <div>
              <p className="text-[#4A7BF7] text-sm font-medium mb-1 animate-pulse">Researching...</p>
              <p className="text-[#94A3B8] text-xs">Gathering findings across the web</p>
            </div>
          </div>
        )}

        {!isEmpty && (
          <div className="aria-output animate-fade-in">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {displayOutput}
            </ReactMarkdown>
            {isStreaming && (
              <span className="inline-block w-2 h-5 bg-[#4A7BF7] animate-pulse ml-1 align-middle rounded-sm" />
            )}
          </div>
        )}
      </div>
    </div>
  )
}
