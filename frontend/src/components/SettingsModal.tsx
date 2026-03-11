import { useState, useEffect } from 'react'
import { createPortal } from 'react-dom'
import { X, Key, Save, Trash2, CheckCircle2 } from 'lucide-react'

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''

interface Provider {
    id: string
    name: string
    requires_key: boolean
    has_key: boolean
    free_tier: boolean
}

interface Props {
    isOpen: boolean
    onClose: () => void
}

export function SettingsModal({ isOpen, onClose }: Props) {
    const [providers, setProviders] = useState<Provider[]>([])
    const [loading, setLoading] = useState(true)
    const [editingProvider, setEditingProvider] = useState<string | null>(null)
    const [apiKey, setApiKey] = useState('')

    const fetchProviders = async () => {
        try {
            setLoading(true)
            const res = await fetch(`${API_BASE}/api/v1/settings/providers`)
            const data = await res.json()
            setProviders(data.providers || [])
        } catch (e) {
            console.error("Failed to fetch config", e)
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        if (isOpen) {
            fetchProviders()
        } else {
            setEditingProvider(null)
            setApiKey('')
        }
    }, [isOpen])

    const handleSaveKey = async (providerId: string) => {
        if (!apiKey.trim()) return
        try {
            await fetch(`${API_BASE}/api/v1/settings/provider`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ provider: providerId, api_key: apiKey.trim() })
            })
            setApiKey('')
            setEditingProvider(null)
            await fetchProviders()
        } catch (e) {
            console.error("Failed to save key", e)
        }
    }

    const handleDeleteKey = async (providerId: string) => {
        try {
            await fetch(`${API_BASE}/api/v1/settings/provider/${providerId}/key`, {
                method: 'DELETE'
            })
            await fetchProviders()
        } catch (e) {
            console.error("Failed to delete key", e)
        }
    }

    if (!isOpen) return null

    return createPortal(
        <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-slate-900/50 backdrop-blur-sm p-4">
            <div className="bg-white rounded-2xl w-full max-w-md shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
                <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <Key size={20} className="text-slate-700" />
                        <h2 className="text-lg font-semibold text-slate-800 tracking-tight">API Keys & Settings</h2>
                    </div>
                    <button onClick={onClose} className="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg transition-colors">
                        <X size={20} />
                    </button>
                </div>

                <div className="p-6 overflow-y-auto">
                    {loading ? (
                        <div className="flex justify-center p-8">
                            <div className="animate-spin rounded-full h-8 w-8 border-2 border-blue-600 border-t-transparent"></div>
                        </div>
                    ) : (
                        <div className="space-y-4">
                            {providers.map(provider => (
                                <div key={provider.id} className="border border-slate-200 rounded-xl p-4 transition-colors hover:border-slate-300">
                                    <div className="flex items-center justify-between mb-2">
                                        <div className="font-medium text-slate-800 text-sm">{provider.name}</div>
                                        <div className="flex items-center gap-2">
                                            {provider.has_key ? (
                                                <span className="flex items-center gap-1 text-[11px] font-medium text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full">
                                                    <CheckCircle2 size={12} /> Configured
                                                </span>
                                            ) : (
                                                <span className="text-[11px] font-medium text-amber-600 bg-amber-50 px-2 py-0.5 rounded-full">Missing Key</span>
                                            )}
                                        </div>
                                    </div>

                                    {editingProvider === provider.id ? (
                                        <div className="flex items-center gap-2 mt-3">
                                            <input
                                                type="password"
                                                placeholder="Enter API Key"
                                                className="flex-1 px-3 py-1.5 text-sm border border-slate-300 rounded-md outline-none focus:border-blue-500 w-full"
                                                value={apiKey}
                                                onChange={e => setApiKey(e.target.value)}
                                                autoFocus
                                                onKeyDown={e => e.key === 'Enter' && handleSaveKey(provider.id)}
                                            />
                                            <button
                                                onClick={() => handleSaveKey(provider.id)}
                                                disabled={!apiKey.trim()}
                                                className="p-1.5 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 transition-colors"
                                                title="Save Key"
                                            >
                                                <Save size={16} />
                                            </button>
                                            <button
                                                onClick={() => { setEditingProvider(null); setApiKey(''); }}
                                                className="p-1.5 bg-slate-100 text-slate-600 rounded-md hover:bg-slate-200 transition-colors"
                                                title="Cancel"
                                            >
                                                <X size={16} />
                                            </button>
                                        </div>
                                    ) : (
                                        <div className="flex items-center gap-2 mt-2">
                                            <button
                                                onClick={() => setEditingProvider(provider.id)}
                                                className="text-xs font-medium text-blue-600 hover:text-blue-700 flex items-center gap-1"
                                            >
                                                {provider.has_key ? 'Update Key' : 'Add Key'}
                                            </button>
                                            {provider.has_key && (
                                                <>
                                                    <span className="text-slate-300 text-xs">|</span>
                                                    <button
                                                        onClick={() => handleDeleteKey(provider.id)}
                                                        className="text-xs font-medium text-red-600 hover:text-red-700 flex items-center gap-1"
                                                    >
                                                        Delete Key
                                                    </button>
                                                </>
                                            )}
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </div>,
        document.body
    )
}
