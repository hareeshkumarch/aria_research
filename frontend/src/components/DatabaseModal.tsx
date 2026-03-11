import { useState, useEffect } from 'react'
import { createPortal } from 'react-dom'
import { X, Database, RefreshCw, Trash2, ChevronDown, ChevronRight, HardDrive, Table2, Activity, Wrench, Radio, Clock, AlertTriangle, CheckCircle2, XCircle } from 'lucide-react'

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''

interface DBStats {
    tables: Record<string, number>
    db_size_bytes: number
    db_size_mb: number
}

interface Props {
    isOpen: boolean
    onClose: () => void
}

const TABLE_META: Record<string, { label: string; icon: any; color: string; description: string }> = {
    runs: { label: 'Runs', icon: Activity, color: 'text-blue-500', description: 'All research runs' },
    subtasks: { label: 'Subtasks', icon: Table2, color: 'text-emerald-500', description: 'Tasks decomposed from each run' },
    tool_calls: { label: 'Tool Calls', icon: Wrench, color: 'text-amber-500', description: 'Tool executions (search, fetch, etc.)' },
    run_events: { label: 'Events', icon: Radio, color: 'text-purple-500', description: 'SSE events emitted per run' },
}

function StatusBadge({ status }: { status: string }) {
    const map: Record<string, { bg: string; text: string; icon: any }> = {
        completed: { bg: 'bg-emerald-50', text: 'text-emerald-600', icon: CheckCircle2 },
        running: { bg: 'bg-blue-50', text: 'text-blue-600', icon: Activity },
        error: { bg: 'bg-red-50', text: 'text-red-600', icon: XCircle },
        pending: { bg: 'bg-slate-50', text: 'text-slate-500', icon: Clock },
        done: { bg: 'bg-emerald-50', text: 'text-emerald-600', icon: CheckCircle2 },
        failed: { bg: 'bg-red-50', text: 'text-red-600', icon: XCircle },
    }
    const s = map[status] || map.pending
    const Icon = s.icon
    return (
        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold ${s.bg} ${s.text}`}>
            <Icon size={10} /> {status}
        </span>
    )
}

function formatDate(dateStr: string | null | undefined) {
    if (!dateStr) return '—'
    try {
        return new Date(dateStr).toLocaleString(undefined, {
            month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit'
        })
    } catch { return dateStr }
}

function truncate(str: string | null | undefined, len: number = 80) {
    if (!str) return '—'
    return str.length > len ? str.substring(0, len) + '…' : str
}

export function DatabaseModal({ isOpen, onClose }: Props) {
    const [stats, setStats] = useState<DBStats | null>(null)
    const [activeTable, setActiveTable] = useState<string>('runs')
    const [tableData, setTableData] = useState<any[]>([])
    const [loading, setLoading] = useState(false)
    const [refreshing, setRefreshing] = useState(false)
    const [expandedRow, setExpandedRow] = useState<string | null>(null)
    const [clearing, setClearing] = useState<string | null>(null)
    const [filterRunId, setFilterRunId] = useState<string>('')

    const fetchStats = async () => {
        try {
            const res = await fetch(`${API_BASE}/api/v1/database/stats`)
            if (res.ok) setStats(await res.json())
        } catch (e) { console.error('Failed to fetch DB stats', e) }
    }

    const fetchTable = async (table?: string) => {
        const t = table || activeTable
        setLoading(true)
        try {
            const endpoint = t === 'run_events' ? 'events' : t
            const params = new URLSearchParams({ limit: '100' })
            if (filterRunId && t !== 'runs') params.set('run_id', filterRunId)
            const res = await fetch(`${API_BASE}/api/v1/database/${endpoint}?${params}`)
            if (res.ok) {
                const data = await res.json()
                setTableData(data.rows || [])
            }
        } catch (e) { console.error('Failed to fetch table data', e) }
        finally { setLoading(false) }
    }

    const handleRefresh = async () => {
        setRefreshing(true)
        try {
            await Promise.all([fetchStats(), fetchTable()])
        } finally {
            setRefreshing(false)
        }
    }

    const clearTable = async (tableName: string) => {
        if (!confirm(`Are you sure you want to clear all data from "${tableName}"? This cannot be undone.`)) return
        setClearing(tableName)
        try {
            await fetch(`${API_BASE}/api/v1/database/table/${tableName}`, { method: 'DELETE' })
            await fetchStats()
            await fetchTable()
        } catch (e) { console.error('Failed to clear table', e) }
        finally { setClearing(null) }
    }

    useEffect(() => {
        if (isOpen) {
            fetchStats()
            fetchTable()
        } else {
            setExpandedRow(null)
            setFilterRunId('')
        }
    }, [isOpen])

    useEffect(() => {
        if (isOpen) fetchTable()
    }, [activeTable, filterRunId])

    if (!isOpen) return null

    const renderRunsTable = () => (
        <div className="space-y-1">
            {tableData.map((row: any) => {
                const isExpanded = expandedRow === row.id
                return (
                    <div key={row.id} className="border border-slate-200 rounded-lg overflow-hidden">
                        <button
                            onClick={() => setExpandedRow(isExpanded ? null : row.id)}
                            className="w-full flex items-center gap-3 px-4 py-3 hover:bg-slate-50 transition-colors text-left"
                        >
                            {isExpanded ? <ChevronDown size={14} className="text-slate-400 shrink-0" /> : <ChevronRight size={14} className="text-slate-400 shrink-0" />}
                            <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2 mb-1">
                                    <span className="text-[12px] font-semibold text-slate-800 truncate">{truncate(row.goal, 60)}</span>
                                    <StatusBadge status={row.status} />
                                </div>
                                <div className="flex items-center gap-3 text-[10px] text-slate-400 font-mono">
                                    <span>{row.id?.substring(0, 8)}</span>
                                    <span>{formatDate(row.created_at)}</span>
                                    {row.critic_score ? <span>⚖️ {row.critic_score}/10</span> : null}
                                    {row.total_tokens ? <span>🪙 {row.total_tokens}</span> : null}
                                </div>
                            </div>
                            <button
                                onClick={(e) => { e.stopPropagation(); setFilterRunId(row.id); setActiveTable('subtasks') }}
                                className="text-[10px] text-blue-500 hover:text-blue-700 font-medium shrink-0"
                            >View Data →</button>
                        </button>
                        {isExpanded && (
                            <div className="px-4 pb-3 pt-1 bg-slate-50/50 border-t border-slate-100 grid grid-cols-2 gap-2 text-[11px]">
                                <div><span className="text-slate-400 font-medium">ID:</span> <span className="font-mono text-slate-600">{row.id}</span></div>
                                <div><span className="text-slate-400 font-medium">Status:</span> <span className="text-slate-600">{row.status}</span></div>
                                <div><span className="text-slate-400 font-medium">Created:</span> <span className="text-slate-600">{formatDate(row.created_at)}</span></div>
                                <div><span className="text-slate-400 font-medium">Completed:</span> <span className="text-slate-600">{formatDate(row.completed_at)}</span></div>
                                <div><span className="text-slate-400 font-medium">Tokens:</span> <span className="text-slate-600">{row.total_tokens ?? '—'}</span></div>
                                <div><span className="text-slate-400 font-medium">Cost:</span> <span className="text-slate-600">{row.total_cost != null ? `$${row.total_cost.toFixed(4)}` : '—'}</span></div>
                                <div><span className="text-slate-400 font-medium">Critic:</span> <span className="text-slate-600">{row.critic_score ?? '—'}</span></div>
                                <div><span className="text-slate-400 font-medium">Updated:</span> <span className="text-slate-600">{formatDate(row.updated_at)}</span></div>
                                {row.error_detail && <div className="col-span-2"><span className="text-red-400 font-medium">Error:</span> <span className="text-red-600">{row.error_detail}</span></div>}
                                {row.final_output && <div className="col-span-2"><span className="text-slate-400 font-medium">Output:</span> <span className="text-slate-600">{truncate(row.final_output, 200)}</span></div>}
                            </div>
                        )}
                    </div>
                )
            })}
        </div>
    )

    const renderSubtasksTable = () => (
        <div className="space-y-1">
            {tableData.map((row: any, i: number) => (
                <div key={row.id || i} className="border border-slate-200 rounded-lg px-4 py-2.5">
                    <div className="flex items-center gap-2 mb-1">
                        <span className="text-[12px] font-semibold text-slate-800">{row.title || '—'}</span>
                        <StatusBadge status={row.status} />
                    </div>
                    <div className="text-[11px] text-slate-500 mb-1">{truncate(row.query || row.description, 120)}</div>
                    <div className="flex items-center gap-3 text-[10px] text-slate-400 font-mono">
                        <span>Run: {row.run_id?.substring(0, 8)}</span>
                        <span>Tool: {row.tool_hint || '—'}</span>
                        <span>{formatDate(row.created_at)}</span>
                    </div>
                </div>
            ))}
        </div>
    )

    const renderToolCallsTable = () => (
        <div className="space-y-1">
            {tableData.map((row: any, i: number) => {
                const isExpanded = expandedRow === (row.id || `tc-${i}`)
                return (
                    <div key={row.id || i} className="border border-slate-200 rounded-lg overflow-hidden">
                        <button
                            onClick={() => setExpandedRow(isExpanded ? null : (row.id || `tc-${i}`))}
                            className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-slate-50 transition-colors text-left"
                        >
                            {isExpanded ? <ChevronDown size={14} className="text-slate-400 shrink-0" /> : <ChevronRight size={14} className="text-slate-400 shrink-0" />}
                            <Wrench size={13} className="text-amber-500 shrink-0" />
                            <span className="text-[12px] font-semibold text-slate-800">{row.tool_name}</span>
                            <span className={`text-[10px] font-medium ${row.success ? 'text-emerald-600' : 'text-red-500'}`}>{row.success ? '✓ Success' : '✗ Failed'}</span>
                            <span className="text-[10px] text-slate-400 font-mono ml-auto">{row.duration_ms}ms</span>
                        </button>
                        {isExpanded && (
                            <div className="px-4 pb-3 pt-1 bg-slate-50/50 border-t border-slate-100 space-y-2 text-[11px]">
                                <div><span className="text-slate-400 font-medium">Run:</span> <span className="font-mono text-slate-600">{row.run_id}</span></div>
                                <div><span className="text-slate-400 font-medium">Input:</span> <pre className="text-slate-600 mt-1 p-2 bg-white rounded border text-[10px] overflow-x-auto max-h-32 overflow-y-auto">{truncate(row.input_data, 500)}</pre></div>
                                <div><span className="text-slate-400 font-medium">Output:</span> <pre className="text-slate-600 mt-1 p-2 bg-white rounded border text-[10px] overflow-x-auto max-h-32 overflow-y-auto">{truncate(row.output_data, 500)}</pre></div>
                            </div>
                        )}
                    </div>
                )
            })}
        </div>
    )

    const renderEventsTable = () => (
        <div className="space-y-1">
            {tableData.map((row: any, i: number) => (
                <div key={row.id || i} className="border border-slate-200 rounded-lg px-4 py-2 flex items-center gap-3">
                    <Radio size={12} className="text-purple-400 shrink-0" />
                    <span className="text-[11px] font-semibold text-purple-600 bg-purple-50 px-2 py-0.5 rounded min-w-[100px] text-center">{row.event_type}</span>
                    <span className="text-[11px] text-slate-500">{row.node || '—'}</span>
                    <span className="text-[10px] text-slate-400 font-mono ml-auto">{formatDate(row.created_at)}</span>
                </div>
            ))}
        </div>
    )

    const renderTable = () => {
        if (loading) return <div className="flex justify-center py-12"><div className="animate-spin rounded-full h-8 w-8 border-2 border-blue-600 border-t-transparent" /></div>
        if (tableData.length === 0) return <div className="text-center py-12 text-slate-400 text-sm">No data in this table</div>
        switch (activeTable) {
            case 'runs': return renderRunsTable()
            case 'subtasks': return renderSubtasksTable()
            case 'tool_calls': return renderToolCallsTable()
            case 'run_events': return renderEventsTable()
            default: return null
        }
    }

    return createPortal(
        <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-slate-900/50 backdrop-blur-sm p-4">
            <div className="bg-white rounded-2xl w-full max-w-4xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
                {/* Header */}
                <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between shrink-0">
                    <div className="flex items-center gap-3">
                        <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center shadow-md">
                            <Database size={18} className="text-white" />
                        </div>
                        <div>
                            <h2 className="text-lg font-semibold text-slate-800 tracking-tight">Database Explorer</h2>
                            {stats && <p className="text-[11px] text-slate-400 font-medium">{stats.db_size_mb} MB • {Object.values(stats.tables).reduce((a, b) => a + b, 0)} total records</p>}
                        </div>
                    </div>
                    <div className="flex items-center gap-2">
                        <button
                            onClick={handleRefresh}
                            disabled={refreshing}
                            className="p-2 text-slate-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors disabled:opacity-60"
                            title="Refresh"
                        >
                            <RefreshCw size={16} className={refreshing ? 'animate-spin' : ''} />
                        </button>
                        <button onClick={onClose} className="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg transition-colors">
                            <X size={18} />
                        </button>
                    </div>
                </div>

                {/* Table Stats Bar */}
                {stats && (
                    <div className="px-6 py-3 border-b border-slate-100 flex items-center gap-2 shrink-0 overflow-x-auto">
                        {Object.entries(TABLE_META).map(([key, meta]) => {
                            const Icon = meta.icon
                            const count = stats.tables[key] ?? 0
                            const isActive = activeTable === key
                            return (
                                <button
                                    key={key}
                                    onClick={() => { setActiveTable(key); setExpandedRow(null) }}
                                    className={`flex items-center gap-2 px-4 py-2 rounded-xl text-[12px] font-semibold transition-all whitespace-nowrap ${isActive
                                            ? 'bg-blue-50 text-blue-700 border border-blue-200 shadow-sm'
                                            : 'text-slate-500 hover:bg-slate-50 border border-transparent'
                                        }`}
                                >
                                    <Icon size={14} className={isActive ? 'text-blue-500' : meta.color} />
                                    {meta.label}
                                    <span className={`px-1.5 py-0.5 rounded-full text-[10px] font-bold ${isActive ? 'bg-blue-100 text-blue-600' : 'bg-slate-100 text-slate-400'
                                        }`}>{count}</span>
                                </button>
                            )
                        })}

                        <div className="ml-auto flex items-center gap-2">
                            {filterRunId && (
                                <div className="flex items-center gap-1.5 bg-amber-50 border border-amber-200 rounded-lg px-3 py-1.5">
                                    <span className="text-[10px] text-amber-600 font-medium">Run: {filterRunId.substring(0, 8)}…</span>
                                    <button onClick={() => setFilterRunId('')} className="text-amber-400 hover:text-amber-600"><X size={12} /></button>
                                </div>
                            )}
                            <button
                                onClick={() => clearTable(activeTable)}
                                disabled={clearing !== null}
                                className="flex items-center gap-1.5 px-3 py-1.5 text-[11px] font-medium text-red-500 hover:bg-red-50 rounded-lg transition-colors disabled:opacity-50"
                                title={`Clear all ${TABLE_META[activeTable]?.label || activeTable}`}
                            >
                                <Trash2 size={12} />
                                {clearing === activeTable ? 'Clearing...' : 'Clear'}
                            </button>
                        </div>
                    </div>
                )}

                {/* Table Content */}
                <div className="flex-1 overflow-y-auto p-4 space-y-1">
                    {renderTable()}
                </div>

                {/* Footer */}
                <div className="px-6 py-3 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-400 shrink-0">
                    <span><HardDrive size={12} className="inline mr-1" />SQLite • {stats?.db_size_mb ?? '—'} MB</span>
                    <span>Showing {tableData.length} records (max 100)</span>
                </div>
            </div>
        </div>,
        document.body
    )
}
