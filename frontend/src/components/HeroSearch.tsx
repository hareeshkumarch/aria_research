import { useState, useRef, useEffect, useMemo } from 'react'
import { useARIAStore } from '../store'
import { Zap, Command, Sparkles, Box, Bot, ChevronDown, Check, Layers, Cpu, Activity, Globe, Database, BookOpen, Microscope, Code } from 'lucide-react'
import { useRunStream } from '../hooks/useRunStream'

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''

const PROVIDERS = [
    { id: 'Groq', label: 'Groq', icon: Zap, color: 'text-amber-500' },
    { id: 'Gemini', label: 'Google Gemini', icon: Bot, color: 'text-blue-500' },
    { id: 'OpenAI', label: 'OpenAI', icon: Command, color: 'text-emerald-500' },
    { id: 'Anthropic', label: 'Anthropic', icon: Sparkles, color: 'text-orange-500' },
    { id: 'Grok', label: 'xAI Grok', icon: Globe, color: 'text-purple-500' },
    { id: 'Ollama', label: 'Ollama (Local)', icon: Box, color: 'text-slate-500' },
]

const MODELS_BY_PROVIDER: Record<string, { value: string; label: string }[]> = {
    'Groq': [
        { value: 'auto', label: 'Auto' },
        { value: 'llama-3.3-70b-versatile', label: 'Llama 3.3 70B' },
        { value: 'llama-3.1-70b-versatile', label: 'Llama 3.1 70B' },
        { value: 'llama-3.1-8b-instant', label: 'Llama 3.1 8B' },
        { value: 'llama-3.2-1b-preview', label: 'Llama 3.2 1B' },
        { value: 'llama-3.2-3b-preview', label: 'Llama 3.2 3B' },
        { value: 'llama-3.2-11b-vision-preview', label: 'Llama 3.2 11B (Vision)' },
        { value: 'llama-3.2-90b-vision-preview', label: 'Llama 3.2 90B (Vision)' },
        { value: 'mixtral-8x7b-32768', label: 'Mixtral 8x7B' },
        { value: 'gemma2-9b-it', label: 'Gemma 2 9B' },
        { value: 'deepseek-r1-distill-llama-70b', label: 'DeepSeek R1 (Llama 70B)' },
    ],
    'Gemini': [
        { value: 'auto', label: 'Auto' },
        { value: 'gemini-2.0-flash', label: 'Gemini 2.0 Flash' },
        { value: 'gemini-2.0-flash-lite', label: 'Gemini 2.0 Flash Lite' },
        { value: 'gemini-pro-latest', label: 'Gemini Pro' },
        { value: 'gemini-flash-latest', label: 'Gemini Flash' },
        { value: 'gemini-1.5-pro', label: 'Gemini 1.5 Pro' },
        { value: 'gemini-1.5-flash', label: 'Gemini 1.5 Flash' },
        { value: 'gemini-1.5-flash-8b', label: 'Gemini 1.5 Flash 8B' },
        { value: 'gemini-1.0-pro', label: 'Gemini 1.0 Pro' },
    ],
    'OpenAI': [
        { value: 'auto', label: 'Auto' },
        { value: 'gpt-4o-mini', label: 'GPT-4o Mini' },
        { value: 'gpt-4o', label: 'GPT-4o' },
        { value: 'gpt-4-turbo', label: 'GPT-4 Turbo' },
        { value: 'gpt-3.5-turbo', label: 'GPT-3.5 Turbo' },
        { value: 'o1-mini', label: 'o1 Mini' },
    ],
    'Anthropic': [
        { value: 'auto', label: 'Auto' },
        { value: 'claude-3-5-sonnet-20241022', label: 'Claude 3.5 Sonnet' },
        { value: 'claude-3-5-haiku-20241022', label: 'Claude 3.5 Haiku' },
        { value: 'claude-3-opus-20240229', label: 'Claude 3 Opus' },
    ],
    'Grok': [
        { value: 'auto', label: 'Auto' },
        { value: 'grok-2-latest', label: 'Grok 2' },
        { value: 'grok-2-1212', label: 'Grok 2 (1212)' },
    ],
    'Ollama': [
        { value: 'auto', label: 'Auto' },
        { value: 'llama3.2', label: 'Llama 3.2' },
        { value: 'llama3.1', label: 'Llama 3.1' },
        { value: 'mistral', label: 'Mistral' },
        { value: 'codellama', label: 'Code Llama' },
        { value: 'phi3', label: 'Phi 3' },
    ]
}

export function HeroSearch() {
    const { status } = useARIAStore()
    const { startAgent } = useRunStream()
    const [prompt, setPrompt] = useState('')
    const [mode, setMode] = useState<'fast' | 'deep'>('fast')
    const [provider, setProvider] = useState('Groq')
    const [modelValue, setModelValue] = useState('auto')

    const [isModeOpen, setIsModeOpen] = useState(false)
    const [isProviderOpen, setIsProviderOpen] = useState(false)
    const [isModelOpen, setIsModelOpen] = useState(false)

    const modeRef = useRef<HTMLDivElement>(null)
    const providerRef = useRef<HTMLDivElement>(null)
    const modelRef = useRef<HTMLDivElement>(null)
    const textareaRef = useRef<HTMLTextAreaElement>(null)

    const [suggestions, setSuggestions] = useState<{ text: string, icon: any }[]>([])
    const [isLoadingSuggestions, setIsLoadingSuggestions] = useState(true)
    const [error, setError] = useState<string | null>(null)

    const examplePrompt = "Compare edge vs cloud for IoT: cost, latency, reliability, and when to choose each."
    const canStart = prompt.trim().length > 0 && status !== 'running'

    useEffect(() => {
        function handleClickOutside(event: MouseEvent) {
            if (modeRef.current && !modeRef.current.contains(event.target as Node)) setIsModeOpen(false)
            if (providerRef.current && !providerRef.current.contains(event.target as Node)) setIsProviderOpen(false)
            if (modelRef.current && !modelRef.current.contains(event.target as Node)) setIsModelOpen(false)
        }
        document.addEventListener('mousedown', handleClickOutside)
        return () => document.removeEventListener('mousedown', handleClickOutside)
    }, [])

    useEffect(() => {
        setIsLoadingSuggestions(true)
        fetch(`${API_BASE}/api/v1/suggestions`)
            .then(res => res.json())
            .then(data => {
                if (data && data.suggestions) {
                    setSuggestions(data.suggestions.map((s: any) => ({ text: s.label, icon: <span>{s.icon}</span> })))
                }
            })
            .catch(err => console.error("Failed to fetch suggestions:", err))
            .finally(() => setIsLoadingSuggestions(false))
    }, [])

    const handleStart = async () => {
        if (!canStart) return
        setError(null)

        // Always include the provider if it's not a global 'auto'
        const pId = provider.toLowerCase()
        const modelStr = modelValue === 'auto' ? `${pId}/auto` : `${pId}/${modelValue}`

        try {
            await startAgent(prompt, mode, modelStr)
            setPrompt('')
        } catch (err: any) {
            setError(err.message || 'Failed to initialize agent run')
        }
    }

    const selectedProvider = PROVIDERS.find(p => p.id === provider) || PROVIDERS[0]
    const currentModels = MODELS_BY_PROVIDER[selectedProvider.id] || MODELS_BY_PROVIDER['Groq']
    const selectedModelLabel = currentModels.find(m => m.value === modelValue)?.label || currentModels[0].label

    // Replace hardcoded ALL_SUGGESTIONS with fetched suggestions
    const randomSuggestions = useMemo(() => {
        if (!suggestions.length) return []
        // Fisher-Yates shuffle
        const shuffled = [...suggestions]
        for (let i = shuffled.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]]
        }
        return shuffled.slice(0, 4)
    }, [suggestions])

    const handleSuggestionClick = (text: string) => {
        setPrompt(text)
        if (textareaRef.current) {
            textareaRef.current.value = text
            textareaRef.current.style.height = 'auto'
            const scrollHeight = textareaRef.current.scrollHeight
            textareaRef.current.style.height = scrollHeight <= 110 ? scrollHeight + 'px' : '110px'
            textareaRef.current.focus()
        }
    }

    return (
        <div className="w-full flex flex-col gap-2 pt-2">
            <div className="px-2 flex flex-col items-center sm:items-start">
                <div className="flex flex-wrap items-center justify-center sm:justify-start gap-2 mb-1 w-full max-w-[800px]">
                    {randomSuggestions.map((s, i) => (
                        <button
                            key={i}
                            onClick={() => handleSuggestionClick(s.text)}
                            className="px-3 py-1.5 bg-white hover:bg-slate-50 text-slate-600 rounded-full text-[12px] font-medium transition-colors text-left flex items-center gap-2 border border-slate-200 shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40 focus-visible:ring-offset-2"
                        >
                            {s.icon}
                            <span>{s.text}</span>
                        </button>
                    ))}
                </div>

                <h1 className="text-[32px] font-bold text-[#1E293B] tracking-tight text-center sm:text-left">Ask ARIA to Research Anything</h1>
                <p className="text-slate-500 mt-2 text-[15px] font-medium text-center sm:text-left">ARIA autonomously plans, searches, analyzes and synthesizes knowledge.</p>
            </div>

            <div className="bg-white rounded-[16px] p-4 shadow-sm border border-[#E5E7EB] flex flex-col relative z-20 transition-shadow focus-within:shadow-[0_6px_30px_rgba(37,99,235,0.10)] focus-within:border-blue-200">

                <div className="relative">
                    <textarea
                        disabled={status === 'running'}
                        ref={textareaRef}
                        placeholder={isLoadingSuggestions ? "Loading workspace..." : "Ask ARIA to research anything…"}
                        className="w-full bg-transparent resize-none outline-none text-slate-700 placeholder-slate-400 text-[15px] px-2 py-1 min-h-[56px] leading-[1.6] [&::-webkit-scrollbar]:hidden [-ms-overflow-style:none] [scrollbar-width:none] disabled:opacity-50"
                        style={{ maxHeight: '120px' }}
                        rows={1}
                        value={prompt}
                        onChange={e => {
                            setPrompt(e.target.value)
                            e.target.style.height = 'auto';
                            e.target.style.height = e.target.scrollHeight <= 120 ? e.target.scrollHeight + 'px' : '120px';
                        }}
                        onKeyDown={e => {
                            if (e.key === 'Enter' && !e.shiftKey) {
                                e.preventDefault()
                                handleStart()
                            }
                        }}
                    />
                </div>

                <div className="mx-2 mt-1.5 text-[12px] text-slate-500 flex flex-wrap items-center gap-2">
                    <span className="font-medium text-slate-500">Try:</span>
                    <button
                        type="button"
                        onClick={() => handleSuggestionClick(examplePrompt)}
                        disabled={status === 'running'}
                        className="text-left text-blue-600 hover:text-blue-700 hover:underline disabled:opacity-50 disabled:no-underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40 focus-visible:ring-offset-2 rounded"
                        title="Insert example prompt"
                    >
                        {examplePrompt}
                    </button>
                </div>

                {error && (
                    <div className="mx-2 mt-2 p-2 bg-red-50 border border-red-100 rounded text-red-600 text-[13px] font-medium flex items-center gap-2">
                        <Activity size={14} className="shrink-0" />
                        {error}
                    </div>
                )}

                <div className="mt-4 flex flex-col gap-4">
                    <div className="flex flex-wrap items-center justify-between gap-4 pt-4 border-t border-[#F1F5F9]">

                        <div className="relative" ref={modeRef}>
                            <button
                                onClick={() => { setIsModeOpen(!isModeOpen); setIsProviderOpen(false); setIsModelOpen(false); }}
                                className="flex items-center gap-2 bg-[#F8FAFC] border border-[#E5E7EB] hover:bg-slate-50 transition-colors text-slate-700 text-[13px] rounded-[10px] px-4 py-2.5 outline-none font-semibold cursor-pointer min-w-[150px] justify-between focus-visible:ring-2 focus-visible:ring-blue-500/40 focus-visible:ring-offset-2"
                                title="Choose research depth"
                            >
                                <span>Depth: <span className="text-blue-600 ml-1">{mode === 'fast' ? 'Standard' : 'Deep'}</span></span>
                                <ChevronDown size={14} className="text-slate-400" />
                            </button>

                            {isModeOpen && (
                                <div className="absolute bottom-full left-0 mb-2 bg-white border border-[#E5E7EB] rounded-[12px] shadow-xl min-w-[160px] z-[100] py-1">
                                    <button onClick={() => { setMode('fast'); setIsModeOpen(false) }} className="w-full text-left px-4 py-2.5 hover:bg-slate-50 flex items-center justify-between transition-colors text-[13px] font-medium text-slate-700">
                                        Standard {mode === 'fast' && <Check size={14} className="text-[#2563EB]" />}
                                    </button>
                                    <button onClick={() => { setMode('deep'); setIsModeOpen(false) }} className="w-full text-left px-4 py-2.5 hover:bg-slate-50 flex items-center justify-between transition-colors text-[13px] font-medium text-slate-700">
                                        Deep {mode === 'deep' && <Check size={14} className="text-[#2563EB]" />}
                                    </button>
                                </div>
                            )}
                        </div>

                        <div className="flex flex-wrap items-center gap-2.5 w-full md:w-auto justify-end flex-1">

                            <div className="relative" ref={providerRef}>
                                <button
                                    onClick={() => { setIsProviderOpen(!isProviderOpen); setIsModelOpen(false); setIsModeOpen(false); }}
                                    className="flex items-center gap-2 bg-[#F8FAFC] border border-[#E5E7EB] hover:bg-slate-50 transition-colors text-slate-700 text-[13px] rounded-[10px] px-3 py-2.5 outline-none font-semibold cursor-pointer min-w-[150px] justify-between focus-visible:ring-2 focus-visible:ring-blue-500/40 focus-visible:ring-offset-2"
                                    title="Choose provider"
                                >
                                    <div className="flex items-center gap-2">
                                        <selectedProvider.icon size={15} className={`shrink-0 ${selectedProvider.color}`} />
                                        <span className="text-slate-600">Provider:</span>
                                        <span className="text-slate-800">{selectedProvider.label}</span>
                                    </div>
                                    <ChevronDown size={14} className="text-slate-400" />
                                </button>

                                {isProviderOpen && (
                                    <div className="absolute bottom-full right-0 mb-2 bg-white border border-[#E5E7EB] rounded-[12px] shadow-xl min-w-[160px] z-[100] py-1">
                                        {PROVIDERS.map((p) => (
                                            <button
                                                key={p.id}
                                                onClick={() => {
                                                    setProvider(p.id);
                                                    setModelValue(MODELS_BY_PROVIDER[p.id][0].value);
                                                    setIsProviderOpen(false)
                                                }}
                                                className="w-full text-left px-4 py-2.5 hover:bg-slate-50 flex items-center gap-3 transition-colors"
                                            >
                                                <p.icon size={14} className={`shrink-0 ${p.color}`} />
                                                <span className={`text-[13px] flex-1 ${provider === p.id ? 'font-bold text-slate-800' : 'text-slate-600 font-medium'}`}>{p.label}</span>
                                                {provider === p.id && <Check size={14} className="text-[#2563EB] shrink-0" />}
                                            </button>
                                        ))}
                                    </div>
                                )}
                            </div>

                            <div className="relative" ref={modelRef}>
                                <button
                                    onClick={() => { setIsModelOpen(!isModelOpen); setIsProviderOpen(false); setIsModeOpen(false); }}
                                    className="flex items-center gap-2 bg-[#F8FAFC] border border-[#E5E7EB] hover:bg-slate-50 transition-colors text-slate-700 text-[13px] rounded-[10px] px-3 py-2.5 outline-none font-semibold cursor-pointer min-w-[180px] justify-between focus-visible:ring-2 focus-visible:ring-blue-500/40 focus-visible:ring-offset-2"
                                    title="Choose model (or Auto)"
                                >
                                    <span className="truncate">
                                        <span className="text-slate-600">Model:</span> <span className="text-slate-800">{selectedModelLabel}</span>
                                    </span>
                                    <ChevronDown size={14} className="text-slate-400" />
                                </button>

                                {isModelOpen && (
                                    <div className="absolute bottom-full right-0 mb-2 bg-white border border-[#E5E7EB] rounded-[12px] shadow-xl min-w-[180px] z-[100] py-1">
                                        {currentModels.map((m) => (
                                            <button
                                                key={m.value}
                                                onClick={() => { setModelValue(m.value); setIsModelOpen(false) }}
                                                className="w-full text-left px-4 py-2.5 hover:bg-slate-50 flex items-center gap-3 transition-colors"
                                            >
                                                <span className={`text-[13px] flex-1 ${modelValue === m.value ? 'font-bold text-slate-800' : 'text-slate-600 font-medium'}`}>{m.label}</span>
                                                {modelValue === m.value && <Check size={14} className="text-[#2563EB] shrink-0" />}
                                            </button>
                                        ))}
                                    </div>
                                )}
                            </div>

                            <button
                                onClick={handleStart}
                                disabled={!canStart}
                                className="bg-[#2563EB] hover:bg-[#1D4ED8] text-white flex-1 md:flex-none px-6 rounded-[10px] font-semibold text-[14px] flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed transition-all shrink-0 whitespace-nowrap focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40 focus-visible:ring-offset-2"
                                style={{ height: '42px' }}
                            >
                                <span>{status === 'running' ? 'Researching…' : 'Start Research'}</span>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )
}
