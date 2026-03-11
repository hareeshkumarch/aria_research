"""Application wide constants and predefined configuration data."""

# Provider metadata for frontend
PROVIDER_CATALOG = {
    "groq": {
        "name": "Groq",
        "models": [
            "llama-3.3-70b-versatile",
            "llama-3.1-70b-versatile",
            "llama-3.1-8b-instant",
            "llama-3.2-1b-preview",
            "llama-3.2-3b-preview",
            "llama-3.2-11b-vision-preview",
            "llama-3.2-90b-vision-preview",
            "mixtral-8x7b-32768",
            "gemma2-9b-it",
            "deepseek-r1-distill-llama-70b",
        ],
        "default_model": "llama-3.3-70b-versatile",
        "requires_key": True,
        "free_tier": True,
    },
    "gemini": {
        "name": "Google Gemini",
        "models": [
            "gemini-2.0-flash",
            "gemini-2.0-flash-lite",
            "gemini-pro-latest",
            "gemini-flash-latest",
            "gemini-1.5-pro",
            "gemini-1.5-flash",
            "gemini-1.5-flash-8b",
            "gemini-1.0-pro",
        ],
        "default_model": "gemini-2.0-flash",
        "requires_key": True,
        "free_tier": True,
    },
    "openai": {
        "name": "OpenAI",
        "models": [
            "gpt-4o-mini",
            "gpt-4o",
            "gpt-4-turbo",
            "gpt-3.5-turbo",
            "o1-mini",
        ],
        "default_model": "gpt-4o-mini",
        "requires_key": True,
        "free_tier": False,
    },
    "anthropic": {
        "name": "Anthropic",
        "models": [
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022",
            "claude-3-opus-20240229",
        ],
        "default_model": "claude-3-5-sonnet-20241022",
        "requires_key": True,
        "free_tier": False,
    },
    "grok": {
        "name": "xAI Grok",
        "models": [
            "grok-2-latest",
            "grok-2-1212",
        ],
        "default_model": "grok-2-latest",
        "requires_key": True,
        "free_tier": False,
    },
    "ollama": {
        "name": "Ollama (Local)",
        "models": [
            "llama3.2",
            "llama3.1",
            "mistral",
            "codellama",
            "phi3",
        ],
        "default_model": "llama3.2",
        "requires_key": False,
        "free_tier": True,
    },
}
