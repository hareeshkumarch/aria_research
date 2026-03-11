from typing import TypedDict, List, Optional, Annotated, Literal
from operator import add


class Subtask(TypedDict):
    id: str
    title: str
    query: str
    description: str
    tool_hint: str           # web_search | web_fetch | code_exec | file_read | recall_memory
    status: str              # pending | running | done | failed
    result: Optional[str]
    dependencies: List[str]  # IDs of subtasks that must complete first
    retry_count: int


class NodeResponse(TypedDict, total=False):
    """Standardized response schema for all agent nodes."""
    task_id: str
    status: Literal["success", "retry", "failed"]
    reasoning_summary: str
    key_findings: List[str]
    sources: List[str]
    confidence_score: float    # 0.0 - 10.0
    next_actions: List[str]


class GoalAnalysis(TypedDict, total=False):
    """Structured breakdown of the user's goal."""
    intent: str
    key_entities: List[str]
    scope: str
    expected_output: str
    constraints: List[str]
    ambiguities: List[str]


class ReasoningOutput(TypedDict, total=False):
    """Structured reasoning analysis output."""
    evidence_summary: str
    patterns: List[str]
    contradictions: List[str]
    conclusions: List[str]
    confidence_score: float
    gaps: List[str]


class CostData(TypedDict):
    input_tokens: int
    output_tokens: int
    total_cost: float


class SourceMetadata(TypedDict):
    url: str
    title: str
    credibility_score: float  # 0.0 - 10.0
    relevance_score: float    # 0.0 - 10.0
    rationale: str


class EvidenceFact(TypedDict):
    fact: str
    source_url: str
    confidence: float
    context: str  # Original snippet


class EntityRelationship(TypedDict):
    source: str
    target: str
    relationship: str
    evidence: List[str]


class ARIAState(TypedDict):
    goal: str
    run_id: str
    mode: str                                # "fast" or "deep"
    model: Optional[str]
    provider: Optional[str]
    goal_analysis: GoalAnalysis              # from goal_understanding node
    subtasks: List[Subtask]
    current_idx: int                         # which subtask we're executing
    tool_results: Annotated[List[str], add]  # accumulates across executor calls
    
    # --- V2 Advanced Metallurgy ---
    research_strategy: str                   # from strategy_generator
    validated_sources: List[SourceMetadata]  # from source_validator
    extracted_evidence: List[EvidenceFact]   # from evidence_extractor
    knowledge_graph: List[EntityRelationship] # from kg_builder
    hypotheses: List[str]                    # from hypothesis_generator
    debate_log: List[str]                    # from debate_system
    contradictions: List[str]                # from reasoning node
    confidence_score: float                  # overall uncertainty estimation
    
    memory_context: List[str]                # retrieved from ChromaDB
    reasoning_output: ReasoningOutput        # from reasoning node
    draft_output: str                        # pre-critique output
    final_output: str
    critic_score: float                      # 0.0 - 10.0
    critic_feedback: str                     # what the critic said
    retry_count: int                         # number of full critique retries
    cost_data: CostData
    node_timings: dict                       # node_id -> duration_ms
    error_detail: str
