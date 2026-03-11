"""Cost tracking for ARIA agent runs."""


# Cost per million tokens (input) for each provider/model
COST_TABLE = {
    "groq": {
        "llama-3.3-70b-versatile": {"input": 0.0, "output": 0.0},  # Free tier
        "*": {"input": 0.0, "output": 0.0},
    },
    "gemini": {
        "gemini-1.5-flash": {"input": 0.0, "output": 0.0},
        "gemini-flash-latest": {"input": 0.0, "output": 0.0},
        "gemini-pro-latest": {"input": 0.0, "output": 0.0},
        "gemini-2.0-flash": {"input": 0.0, "output": 0.0},
        "*": {"input": 0.0, "output": 0.0},
    },
    "openai": {
        "gpt-4o-mini": {"input": 0.15, "output": 0.60},
        "gpt-4o": {"input": 2.50, "output": 10.00},
        "gpt-4-turbo": {"input": 10.00, "output": 30.00},
        "*": {"input": 2.50, "output": 10.00},
    },
    "anthropic": {
        "claude-sonnet-4-20250514": {"input": 3.00, "output": 15.00},
        "claude-3-5-haiku-20241022": {"input": 0.80, "output": 4.00},
        "*": {"input": 3.00, "output": 15.00},
    },
    "grok": {
        "grok-3-mini": {"input": 0.30, "output": 0.50},
        "*": {"input": 0.30, "output": 0.50},
    },
    "ollama": {
        "*": {"input": 0.0, "output": 0.0},  # Local = free
    },
}


class CostTracker:
    """Tracks token usage and estimated cost for a single run."""

    def __init__(self, provider: str, model: str):
        self.provider = provider
        self.model = model
        self.input_tokens = 0
        self.output_tokens = 0
        self.total_cost = 0.0
        self._breakdown: dict[str, dict] = {}  # node -> {input_tokens, output_tokens, cost}

    def add_usage(self, node: str, input_tokens: int = 0, output_tokens: int = 0):
        """Record token usage for a node."""
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens

        costs = COST_TABLE.get(self.provider, {}).get(
            self.model, COST_TABLE.get(self.provider, {}).get("*", {"input": 0, "output": 0})
        )

        cost = (input_tokens * costs["input"] + output_tokens * costs["output"]) / 1_000_000
        self.total_cost += cost

        if node not in self._breakdown:
            self._breakdown[node] = {"input_tokens": 0, "output_tokens": 0, "cost": 0.0}
        self._breakdown[node]["input_tokens"] += input_tokens
        self._breakdown[node]["output_tokens"] += output_tokens
        self._breakdown[node]["cost"] += cost

    def to_dict(self) -> dict:
        return {
            "provider": self.provider,
            "model": self.model,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_cost": round(self.total_cost, 6),
            "breakdown": self._breakdown,
        }
