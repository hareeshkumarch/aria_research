from langchain_core.language_models.chat_models import BaseChatModel
from .config import get_active_provider, get_active_model, get_api_key, settings


def get_llm(streaming: bool = False, provider: str | None = None, model: str | None = None) -> BaseChatModel:
    """
    Return the configured LLM.
    
    Supports: Groq, Gemini, OpenAI, Anthropic, Grok, Ollama.
    If provider/model are None, uses the active (runtime or env) settings.
    """
    if provider is None or provider == "auto":
        provider = get_active_provider()
    
    if model is None or model == "auto":
        model = get_active_model(provider)

    from .logger import get_logger
    get_logger(__name__).info(f"Initializing LLM: provider={provider}, model={model}")

    # Attach a lightweight callback to emit incremental token/cost updates over SSE.
    # This keeps the "Research Activity" panel live during a run.
    callbacks = []
    try:
        import asyncio
        from langchain_core.callbacks import BaseCallbackHandler
        from .agent.context import get_queue, get_cost_tracker

        class _UsageCallback(BaseCallbackHandler):
            def on_llm_end(self, response, **kwargs):  # type: ignore[override]
                try:
                    prompt = 0
                    completion = 0

                    # 1) Preferred: pull usage from AIMessage.usage_metadata (works across many LangChain providers)
                    try:
                        gens = getattr(response, "generations", None) or []
                        if gens and gens[0] and hasattr(gens[0][0], "message"):
                            msg = gens[0][0].message
                            usage_md = getattr(msg, "usage_metadata", None) or {}
                            prompt = int(usage_md.get("input_tokens") or usage_md.get("prompt_tokens") or prompt)
                            completion = int(usage_md.get("output_tokens") or usage_md.get("completion_tokens") or completion)
                    except Exception:
                        pass

                    # 2) Fallback: response.llm_output token_usage/usage (provider-specific)
                    llm_output = getattr(response, "llm_output", None) or {}
                    usage = llm_output.get("token_usage") or llm_output.get("usage") or {}
                    prompt = int(usage.get("prompt_tokens") or usage.get("input_tokens") or prompt)
                    completion = int(usage.get("completion_tokens") or usage.get("output_tokens") or completion)

                    tracker = get_cost_tracker()
                    queue = get_queue()
                    if tracker and hasattr(tracker, "add_usage"):
                        tracker.add_usage(node="llm", input_tokens=prompt, output_tokens=completion)  # type: ignore[attr-defined]

                    if queue is None:
                        return

                    input_tokens = getattr(tracker, "input_tokens", 0) if tracker else prompt
                    output_tokens = getattr(tracker, "output_tokens", 0) if tracker else completion
                    total_cost = getattr(tracker, "total_cost", 0.0) if tracker else 0.0

                    event = {
                        "type": "cost_update",
                        "input_tokens": int(input_tokens),
                        "output_tokens": int(output_tokens),
                        "total_cost": float(total_cost),
                        "tokens": int(output_tokens),  # backward-compatible field
                        "cost": float(total_cost),     # backward-compatible field
                    }

                    try:
                        loop = asyncio.get_running_loop()
                        loop.create_task(queue.put(event))
                    except RuntimeError:
                        # No running loop (shouldn't happen in normal server execution)
                        pass
                except Exception:
                    # Never allow accounting errors to break the run
                    return

        callbacks = [_UsageCallback()]
    except Exception:
        callbacks = []

    if provider == "groq":
        from langchain_groq import ChatGroq
        return ChatGroq(
            api_key=get_api_key("groq"),
            model=model,
            streaming=streaming,
            temperature=0.1,
            timeout=45.0,
            max_retries=2,
            callbacks=callbacks,
        )

    elif provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            google_api_key=get_api_key("gemini"),
            model=model,
            streaming=streaming,
            temperature=0.1,
            timeout=45.0,
            max_retries=2,
            callbacks=callbacks,
        )

    elif provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            api_key=get_api_key("openai"),
            model=model,
            streaming=streaming,
            temperature=0.1,
            timeout=45.0,
            max_retries=2,
            callbacks=callbacks,
        )

    elif provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            api_key=get_api_key("anthropic"),
            model=model,
            streaming=streaming,
            temperature=0.1,
            timeout=45.0,
            max_retries=2,
            callbacks=callbacks,
        )

    elif provider == "grok":
        # Grok uses OpenAI-compatible API via xAI
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            api_key=get_api_key("grok"),
            model=model,
            streaming=streaming,
            temperature=0.1,
            timeout=45.0,
            max_retries=2,
            base_url="https://api.x.ai/v1",
            callbacks=callbacks,
        )

    elif provider == "ollama":
        from langchain_ollama import ChatOllama
        # We pass num_ctx in multiple ways to ensure it overrides any global defaults
        return ChatOllama(
            base_url=settings.ollama_base_url,
            model=model,
            streaming=streaming,
            timeout=45.0,
            max_retries=2,
            num_ctx=8192,  # Reasonable context for research agent prompts
            num_predict=2048, # Allow longer responses for report synthesis
            # For some versions, it's passed via extra_kwargs
            callbacks=callbacks,
        )

    else:
        raise ValueError(f"Unknown LLM provider: {provider}")

def get_embeddings(provider: str | None = None):
    """
    Return the configured embedding model.
    Matches the provider of the main LLM to keep things simple.
    """
    if provider is None or provider == "auto":
        provider = get_active_provider()

    from .logger import get_logger
    get_logger(__name__).info(f"Initializing Embeddings: provider={provider}")

    if provider == "groq":
        # Groq doesn't host embeddings natively in LangChain standard way yet, we generally use OpenAI or mixed
        # But assuming they might use a fast generic one or we fallback to huggingface
        from langchain_community.embeddings import HuggingFaceEmbeddings
        return HuggingFaceEmbeddings(model_name="BAAI/bge-small-en-v1.5")
        
    elif provider == "gemini":
        from langchain_google_genai import GoogleGenerativeAIEmbeddings
        return GoogleGenerativeAIEmbeddings(
            google_api_key=get_api_key("gemini"),
            model="models/text-embedding-004"
        )
        
    elif provider == "openai":
        from langchain_openai import OpenAIEmbeddings
        return OpenAIEmbeddings(
            api_key=get_api_key("openai"),
            model="text-embedding-3-small"
        )
        
    elif provider == "anthropic":
        # Anthropic doesn't have public embeddings, fallback to HuggingFace
        from langchain_community.embeddings import HuggingFaceEmbeddings
        return HuggingFaceEmbeddings(model_name="BAAI/bge-small-en-v1.5")
        
    elif provider == "grok":
        from langchain_openai import OpenAIEmbeddings
        return OpenAIEmbeddings(
            api_key=get_api_key("grok"),
            model="text-embedding-3-small", 
            base_url="https://api.x.ai/v1"
        )
        
    elif provider == "ollama":
        from langchain_community.embeddings import OllamaEmbeddings
        return OllamaEmbeddings(
            base_url=settings.ollama_base_url,
            model="nomic-embed-text" # Default good ollama embedding model
        )
        
    else:
        from langchain_community.embeddings import HuggingFaceEmbeddings
        return HuggingFaceEmbeddings(model_name="BAAI/bge-small-en-v1.5")
