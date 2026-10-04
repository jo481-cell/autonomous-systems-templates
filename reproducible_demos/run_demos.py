"""Execute three reproducible CPU demonstrations and write evidence artifacts."""
from __future__ import annotations

import json
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

import pydantic
import pytest

from scoped_repair import PatchRejected, function_source, run_pytest, scoped_candidate, try_repair
from state_machine import StateMachine, fixture_decision
from structured_output import InvoicePayload, build_ollama_request, inspect_payload

HERE = Path(__file__).resolve().parent
FIXTURE = 'VERSION = "fixture-v1"\n\ndef divide(a, b):\n    return a * b\n\ndef add(a, b):\n    return a + b\n'
FIXTURE_TESTS = '''from calculator import VERSION, add, divide

def test_division():
    assert divide(10, 2) == 5

def test_unchanged_add():
    assert add(2, 3) == 5

def test_unchanged_version():
    assert VERSION == "fixture-v1"
'''
DISCLOSURE = "Executed CPU demonstration. Decisions and patches are deterministic fixtures. No language model was called."


def save_json(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def step(identifier: str, title: str, command: str, output: str, before: str = "", after: str = "") -> dict:
    assert len(output.splitlines()) <= 8
    return {"id": identifier, "title": title, "command": command, "output": output, "before": before, "after": after}


def demo_states() -> dict:
    machine = StateMachine()
    valid_input = fixture_decision()
    valid = machine.run("Add 2, 3 and 4", valid_input)
    invalid = machine.run("Add 2, 3 and 4", '{"tool": 42, "arguments": {}}')
    blocked = machine.run("Add 2, 3 and 4", fixture_decision("delete_workspace"))
    assert valid["state"] == "COMPLETED" and valid["result"] == 9
    assert invalid["reason"] == "invalid triage payload"
    assert blocked["reason"] == "tool not allowlisted"
    save_json(HERE / "samples" / "state_machine.json", {"decision_source": "deterministic fixture", "valid_input": json.loads(valid_input), "valid": valid, "invalid": invalid, "blocked": blocked})
    return {
        "episode": 4, "title": "A Python Agent with Explicit Failure States", "disclosure": DISCLOSURE,
        "steps": [
            step("state_success", "Explicit states", "machine.run(task, fixture_decision())", "INGESTION -> TRIAGE\nTOOL_EXECUTION -> VERIFICATION\nCOMPLETED: result 9\nDecision: deterministic fixture", valid_input, json.dumps(valid)),
            step("invalid_decision", "Invalid output stops", 'machine.run(task, \'{"tool": 42, "arguments": {}}\')', "FAILED: invalid triage payload", '{"tool": 42, "arguments": {}}', "No tool executed"),
            step("blocked_tool", "Allowlist enforced", 'machine.run(task, fixture_decision("delete_workspace"))', "FAILED: tool not allowlisted", "tool: delete_workspace", "No tool executed"),
        ],
        "checks": {"success_state": True, "invalid_output_stopped": True, "unknown_tool_stopped": True, "model_called": False},
    }


def demo_json() -> dict:
    samples = {
        "syntax_invalid": '{"invoice_id": "INV-0042", "amount": 249.0, "currency": "CAD",}',
        "schema_invalid": '{"invoice_id": "INV-0042", "amount": "249.0", "currency": "CAD"}',
        "semantic_invalid": '{"invoice_id": "INV-0042", "amount": 249.0, "currency": "USD"}',
        "valid_payload": '{"invoice_id": "INV-0042", "amount": 249.0, "currency": "CAD"}',
    }
    results = {key: inspect_payload(raw) for key, raw in samples.items()}
    assert results["syntax_invalid"]["syntax"] == "REJECTED"
    assert results["schema_invalid"]["schema"] == "REJECTED"
    assert results["semantic_invalid"]["semantics"] == "REJECTED"
    assert results["valid_payload"]["semantics"] == "ACCEPTED"
    request = build_ollama_request("Invoice INV-0042: CAD 249.00")
    assert request["format"] == InvoicePayload.model_json_schema() and request["stream"] is False
    save_json(HERE / "samples" / "structured_outputs.json", {"inputs": samples, "results": results})
    save_json(HERE / "samples" / "ollama_request_NOT_EXECUTED.json", request)
    steps = []
    titles = ["JSON syntax", "Required structure", "Meaning and policy", "All three checks"]
    for (key, raw), title in zip(samples.items(), titles):
        result = results[key]
        lines = [f"JSON syntax: {result['syntax']}"]
        if result["schema"] != "NOT CHECKED":
            lines.append(f"Schema: {result['schema']}")
        if result["semantics"] != "NOT CHECKED":
            lines.append(f"Semantic policy: {result['semantics']}")
        steps.append(step(key, title, "inspect_payload(sample)", "\n".join(lines), raw, json.dumps(result)))
    steps.append(step("ollama_request", "Pass the actual schema", "build_ollama_request(prompt)", "format: InvoicePayload.model_json_schema()\nstream: false\nLocal model call: NOT EXECUTED", 'format: "json"', "format: schema object\nstream: false"))
    return {"episode": 5, "title": "Valid JSON Is Only the First Check", "disclosure": DISCLOSURE,
            "steps": steps, "checks": {"syntax_rejection": True, "schema_rejection": True, "semantic_rejection": True, "valid_fixture_accepted": True, "schema_in_format": True, "stream_false": True, "model_called": False}}


def demo_repair() -> dict:
    git = shutil.which("git")
    if not git:
        raise RuntimeError("Git must be available on PATH for the temporary fixture.")
    with TemporaryDirectory(prefix="autonomous_workday_fixture_") as directory:
        workspace = Path(directory)
        initialization = subprocess.run([git, "init", "--quiet", str(workspace)], capture_output=True, text=True, timeout=20)
        if initialization.returncode:
            raise RuntimeError("Temporary fixture git initialization failed: " + initialization.stderr)
        (workspace / "calculator.py").write_bytes(FIXTURE.encode("utf-8"))
        (workspace / "test_calculator.py").write_bytes(FIXTURE_TESTS.encode("utf-8"))
        initial = run_pytest(workspace)
        expected = function_source(FIXTURE, "divide")
        good_patch = "def divide(a, b):\n    return a / b"
        accepted = try_repair(workspace, expected, good_patch)
        accepted_bytes = (workspace / "calculator.py").read_bytes()
        bad_patch = "def divide(a, b):\n    return 0"
        rejected = try_repair(workspace, good_patch, bad_patch)
        assert not initial["passed"] and initial["summary"] == "1 failed, 2 passed"
        assert accepted["accepted"] and accepted["tests"]["summary"] == "3 passed"
        assert not rejected["accepted"] and rejected["original_bytes_restored"]
        assert (workspace / "calculator.py").read_bytes() == accepted_bytes
        try:
            scoped_candidate(accepted_bytes, "divide", good_patch, good_patch + '\n\nVERSION = "modified"')
        except PatchRejected as error:
            boundary_reason = str(error)
        else:
            raise AssertionError("Out-of-function candidate was accepted")
        assert boundary_reason == "edits outside target function"
        save_json(HERE / "samples" / "scoped_repair.json", {
            "patch_source": "deterministic fixture", "initial_source": FIXTURE,
            "tests": FIXTURE_TESTS, "accepted_patch": good_patch, "rejected_patch": bad_patch,
            "initial_summary": initial["summary"], "accepted_summary": accepted["tests"]["summary"],
            "rejected_summary": rejected["tests"]["summary"], "original_bytes_restored": True,
            "git_initialized": True, "git_commits_created": 0, "temporary_workspace_removed_at_exit": True,
        })
        return {
            "episode": 6, "title": "A Scoped Patch with a Real Rollback Check", "disclosure": DISCLOSURE,
            "steps": [
                step("fixture_failed", "A real failing fixture", "python -m pytest -q test_calculator.py", "pytest: " + initial["summary"], expected, "assert divide(10, 2) == 5\nActual result: 20"),
                step("fixture_repaired", "Accept a tested patch", "try_repair(workspace, expected, good_patch)", "pytest: " + accepted["tests"]["summary"] + "\nCandidate: ACCEPTED\nPatch source: deterministic fixture", expected, good_patch),
                step("regression_rejected", "Restore a rejected candidate", "try_repair(workspace, good_patch, bad_patch)", "pytest: " + rejected["tests"]["summary"] + "\nCandidate: REJECTED\nOriginal bytes: RESTORED", bad_patch, good_patch),
                step("boundary_rejected", "Enforce the function boundary", "scoped_candidate(original, 'divide', expected, oversized_patch)", "REJECTED: " + boundary_reason, 'divide patch + VERSION = "modified"', "Outside bytes unchanged"),
            ],
            "checks": {"fixture_tests_failed": True, "accepted_patch_tests_passed": True, "regression_rejected": True, "byte_exact_restore": True, "outside_function_rejected": True, "temporary_git_fixture": True, "model_called": False, "commits_created": 0},
        }


def main() -> None:
    (HERE / "samples").mkdir(exist_ok=True)
    episodes = [demo_states(), demo_json(), demo_repair()]
    result = {
        "schema_version": 1,
        "executed_at_utc": datetime.now(timezone.utc).isoformat(),
        "environment": {"python": platform.python_version(), "pydantic": pydantic.__version__, "pytest": pytest.__version__, "device": "CPU", "models_called": 0, "network_requests": 0},
        "source_status": "New independently authored demonstration code. Existing repository files unchanged.",
        "episodes": episodes,
    }
    save_json(HERE / "demo_results.json", result)
    print("Executed 3 CPU demonstrations.")
    print("EP04: success, invalid triage, unknown tool checks passed.")
    print("EP05: syntax, schema, semantic policy checks passed; no model call.")
    print("EP06: pytest fail -> pass; regression rejected; exact bytes restored.")
    print("Evidence: demo_results.json and samples/")


if __name__ == "__main__":
    main()
