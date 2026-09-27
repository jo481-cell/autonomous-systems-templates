from typing import List, Literal, Optional
from pydantic import BaseModel, Field

class UrgencyLevel(str):
    P1 = "P1"  # Critical / Immediate attention
    P2 = "P2"  # High priority / Blockers
    P3 = "P3"  # Standard backlog
    P4 = "P4"  # Informational / Low

class SentryTriagePayload(BaseModel):
    """Deterministic Pydantic schema enforced on local LLM outputs."""
    urgency: Literal["P1", "P2", "P3", "P4"] = Field(
        ..., description="Triage priority level from P1 (critical) to P4 (low)"
    )
    summary: str = Field(
        ..., max_length=180, description="Distilled executive summary in under 30 words"
    )
    extracted_deadlines: List[str] = Field(
        default_factory=list, description="List of ISO dates or specific timeframes mentioned"
    )
    action_required: bool = Field(
        ..., description="True if next layer execution agent must be dispatched"
    )
    suggested_tool: Optional[Literal["git_diff", "run_unit_tests", "log_analysis", "none"]] = Field(
        default="none", description="Target tool for Layer 2 execution"
    )

class ExecutionResult(BaseModel):
    tool_name: str
    status: Literal["success", "failure", "blocked_requires_override"]
    exit_code: int
    output_summary: str
