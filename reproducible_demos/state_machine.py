"""CPU demonstration of explicit states and tool authorization.

The triage decision is a deterministic fixture, not an LLM response.
This example demonstrates control flow; it is not a security sandbox.
"""
from __future__ import annotations

import json
from enum import Enum
from typing import Callable

from pydantic import BaseModel, ConfigDict, Field, ValidationError


class State(str, Enum):
    INGESTION = "INGESTION"
    TRIAGE = "TRIAGE"
    TOOL_EXECUTION = "TOOL_EXECUTION"
    VERIFICATION = "VERIFICATION"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class TriageDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    tool: str = Field(min_length=1)
    arguments: dict


class SumArguments(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    values: list[int] = Field(min_length=1, max_length=50)


def sum_numbers(arguments: dict) -> int:
    validated = SumArguments.model_validate(arguments)
    return sum(validated.values)


class StateMachine:
    """The registry is the allowlist. No shell command is accepted."""

    def __init__(self) -> None:
        self.tools: dict[str, Callable[[dict], int]] = {"sum_numbers": sum_numbers}

    def run(self, task: str, decision_json: str) -> dict:
        history = [State.INGESTION.value]

        def fail(reason: str) -> dict:
            history.append(State.FAILED.value)
            return {"state": State.FAILED.value, "reason": reason, "history": history}

        if not task.strip():
            return fail("empty task")
        history.append(State.TRIAGE.value)
        try:
            decision = TriageDecision.model_validate_json(decision_json)
        except ValidationError:
            return fail("invalid triage payload")
        if decision.tool not in self.tools:
            return fail("tool not allowlisted")
        history.append(State.TOOL_EXECUTION.value)
        try:
            result = self.tools[decision.tool](decision.arguments)
        except (ValidationError, TypeError, ValueError):
            return fail("invalid tool arguments")
        history.append(State.VERIFICATION.value)
        # This verifier checks this fixture's explicit acceptance criterion.
        if task != "Add 2, 3 and 4" or result != 9:
            return fail("acceptance criterion not satisfied")
        history.append(State.COMPLETED.value)
        return {"state": State.COMPLETED.value, "result": result, "history": history}


def fixture_decision(tool: str = "sum_numbers") -> str:
    return json.dumps({"tool": tool, "arguments": {"values": [2, 3, 4]}})
