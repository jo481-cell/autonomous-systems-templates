"""Separate JSON syntax, schema validation, and business policy.

The local Ollama client is provided for inspection and future use.
It is not called by the CPU demonstrations or tests.
"""
from __future__ import annotations

import json
from typing import Literal
from urllib.request import Request, urlopen

from pydantic import BaseModel, ConfigDict, Field, ValidationError


class InvoicePayload(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    invoice_id: str = Field(pattern=r"^INV-[0-9]{4}$")
    amount: float = Field(gt=0)
    currency: Literal["CAD", "USD"]


def inspect_payload(raw: str) -> dict:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {"syntax": "REJECTED", "schema": "NOT CHECKED", "semantics": "NOT CHECKED"}
    try:
        payload = InvoicePayload.model_validate(parsed)
    except ValidationError:
        return {"syntax": "VALID", "schema": "REJECTED", "semantics": "NOT CHECKED"}
    # An explicit example policy, not a universal rule for invoices.
    approved = payload.currency == "CAD" and payload.amount <= 1000
    return {
        "syntax": "VALID", "schema": "VALID",
        "semantics": "ACCEPTED" if approved else "REJECTED",
        "payload": payload.model_dump(),
        "policy": "CAD invoices only; amount at most 1000",
    }


def build_ollama_request(prompt: str, model: str = "qwen2.5:7b") -> dict:
    schema = InvoicePayload.model_json_schema()
    return {
        "model": model,
        "messages": [
            {"role": "system", "content": "Extract the invoice. Follow this schema: " + json.dumps(schema)},
            {"role": "user", "content": prompt},
        ],
        "format": schema,
        "stream": False,
        "options": {"temperature": 0},
    }


def call_local_ollama(prompt: str, model: str = "qwen2.5:7b") -> InvoicePayload:
    """Optional localhost call. Not executed or integration-tested here.

    Caller must ensure a suitable model is already installed and the local
    Ollama instance is permitted. Schema validity does not establish truth.
    """
    request = Request(
        "http://127.0.0.1:11434/api/chat",
        data=json.dumps(build_ollama_request(prompt, model)).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=60) as response:
        envelope = json.loads(response.read().decode("utf-8"))
    return InvoicePayload.model_validate_json(envelope["message"]["content"])
