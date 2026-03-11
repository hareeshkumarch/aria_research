import { useState } from 'react'
import { Home, Bot, Trash2, Settings, Database, Menu, X } from 'lucide-react'
import { useARIAStore } from '../store'
import { SettingsModal } from './SettingsModal'
import { DatabaseModal } from './DatabaseModal'

export function Sidebar() {
    const { runHistory, viewHistoryRun, deleteRun, reset } = useARIAStore()
    const [hoveredId, setHoveredId] = useState<string | null>(null)
    const [deletingId, setDeletingId] = useState<string | null>(null)
    const [isSettingsOpen, setIsSettingsOpen] = useState(false)
    const [isDbOpen, setIsDbOpen] = useState(false)
    const [isMobileOpen, setIsMobileOpen] = useState(false)

    const handleDelete = async (e: React.MouseEvent, runId: string) => {
        e.stopPropagation()
        setDeletingId(runId)
        await deleteRun(runId)
        setDeletingId(null)
    }

    const sidebarContent = (
        <>
            {/* Top Section */}
            <div className="flex items-center gap-3 px-2 mb-8 mt-2 cursor-pointer" onClick={() => { reset(); setIsMobileOpen(false) }}>
                <div className="w-8 h-8 flex flex-shrink-0 items-center justify-center">
                    <img src="/orbit-icon.svg" alt="ARIA Logo" className="w-full h-full" />
                </div>
                <div>
                    <h1 className="font-bold text-lg text-slate-900 tracking-tight leading-none">ARIA</h1>
                    <p className="text-[10px] text-slate-500 font-medium mt-1 uppercase tracking-wider">Autonomous Research Intelligent Agent</p>
                </div>
            </div>

            {/* Navigation Menu */}
            <nav className="space-y-1 mb-6">
                <button onClick={() => { reset(); setIsMobileOpen(false) }} className="w-full flex items-center gap-3 px-4 py-2.5 bg-[#EFF6FF] text-[#2563EB] rounded-[12px] font-medium text-sm transition-colors">
                    <Home size={18} className="text-[#2563EB]" /> Home
                </button>
                <button onClick={() => setIsSettingsOpen(true)} className="w-full flex items-center gap-3 px-4 py-2.5 text-slate-600 hover:bg-slate-50 hover:text-slate-900 rounded-[12px] font-medium text-sm transition-colors">
                    <Settings size={18} /> Settings
                </button>
                <button onClick={() => setIsDbOpen(true)} className="w-full flex items-center gap-3 px-4 py-2.5 text-slate-600 hover:bg-slate-50 hover:text-slate-900 rounded-[12px] font-medium text-sm transition-colors">
                    <Database size={18} /> Database
                </button>
            </nav>

            <div className="mt-2 flex-1 min-h-0 overflow-y-auto">
                <h4 className="px-4 text-[11px] font-bold text-slate-400 uppercase tracking-widest mb-3">Recent Research</h4>
                <div className="space-y-0.5 px-1">
                    {runHistory.length === 0 ? (
                        <div className="px-4 text-[13px] text-slate-500 italic">
                            No recent history
                        </div>
                    ) : (
                        runHistory.map((run) => (
                            <div
                                key={run.run_id}
                                className="relative group"
                                onMouseEnter={() => setHoveredId(run.run_id)}
                                onMouseLeave={() => setHoveredId(null)}
                            >
                                <button
                                    onClick={() => { viewHistoryRun(run); setIsMobileOpen(false) }}
                                    className="w-full text-left px-3 py-2 rounded-lg text-[12px] text-slate-600 hover:bg-slate-50 hover:text-slate-900 transition-all truncate pr-8"
                                    title={run.goal}
                                >
                                    <span className="mr-1.5 opacity-40 group-hover:opacity-100 italic font-mono text-[10px]">#</span>
                                    {run.goal}
                                </button>
                                {hoveredId === run.run_id && (
                                    <button
                                        onClick={(e) => handleDelete(e, run.run_id)}
                                        disabled={deletingId === run.run_id}
                                        className="absolute right-1 top-1/2 -translate-y-1/2 p-1.5 rounded-md hover:bg-red-50 text-slate-400 hover:text-red-500 transition-all"
                                        title="Delete run"
                                    >
                                        <Trash2 size={13} className={deletingId === run.run_id ? 'animate-pulse' : ''} />
                                    </button>
                                )}
                            </div>
                        ))
                    )}
                </div>
            </div>

            {/* Bottom Section */}
            <div className="mt-auto shrink-0 flex items-center justify-center pt-4 border-t border-[#F1F5F9]">
                <span className="text-xs text-slate-400 font-medium">ARIA v0.1</span>
            </div>
        </>
    )

    return (
        <>
            {/* Mobile Hamburger Button */}
            <button
                onClick={() => setIsMobileOpen(!isMobileOpen)}
                className="lg:hidden fixed top-4 left-4 z-[999] w-10 h-10 rounded-xl bg-white border border-slate-200 shadow-md flex items-center justify-center text-slate-600 hover:text-slate-900 transition-colors"
                aria-label="Toggle navigation"
            >
                {isMobileOpen ? <X size={20} /> : <Menu size={20} />}
            </button>

            {/* Desktop Sidebar */}
            <div className="w-[220px] bg-white h-full flex flex-col p-4 border-r border-[#E5E7EB] sticky top-0 hidden lg:flex shrink-0 overflow-y-auto">
                {sidebarContent}
            </div>

            {/* Mobile Sidebar Overlay */}
            {isMobileOpen && (
                <>
                    <div
                        className="lg:hidden fixed inset-0 bg-black/30 z-[997] backdrop-blur-sm"
                        onClick={() => setIsMobileOpen(false)}
                    />
                    <div className="lg:hidden fixed top-0 left-0 h-full w-[280px] bg-white z-[998] flex flex-col p-4 shadow-2xl overflow-y-auto animate-slide-in">
                        {sidebarContent}
                    </div>
                </>
            )}

            <SettingsModal isOpen={isSettingsOpen} onClose={() => setIsSettingsOpen(false)} />
            <DatabaseModal isOpen={isDbOpen} onClose={() => setIsDbOpen(false)} />
        </>
    )
}
