"""Behavioral checks for authorization, validation layers and reversibility."""
import json
from pathlib import Path

import pytest

from run_demos import FIXTURE, FIXTURE_TESTS
from scoped_repair import PatchRejected, function_source, scoped_candidate, try_repair
from state_machine import StateMachine, fixture_decision
from structured_output import InvoicePayload, build_ollama_request, inspect_payload


def test_unknown_tool_cannot_execute():
    agent = StateMachine()
    result = agent.run("Add 2, 3 and 4", fixture_decision("delete_workspace"))
    assert result["reason"] == "tool not allowlisted"
    assert "TOOL_EXECUTION" not in result["history"]


def test_invalid_triage_cannot_execute():
    result = StateMachine().run("Add 2, 3 and 4", '{"tool": 42}')
    assert result["state"] == "FAILED"
    assert "TOOL_EXECUTION" not in result["history"]


def test_invalid_tool_values_stop_before_verification():
    result = StateMachine().run("Add 2, 3 and 4", json.dumps({"tool": "sum_numbers", "arguments": {"values": ["2", 3, 4]}}))
    assert result["reason"] == "invalid tool arguments"
    assert "VERIFICATION" not in result["history"]


def test_schema_validity_does_not_imply_policy_acceptance():
    valid_json = '{"invoice_id":"INV-0042","amount":249.0,"currency":"USD"}'
    result = inspect_payload(valid_json)
    assert result["syntax"] == "VALID" and result["schema"] == "VALID"
    assert result["semantics"] == "REJECTED"


def test_schema_is_actually_passed_to_ollama():
    request = build_ollama_request("example")
    assert request["format"] == InvoicePayload.model_json_schema()
    assert request["stream"] is False


def test_outside_function_edit_is_rejected():
    expected = function_source(FIXTURE, "divide")
    with pytest.raises(PatchRejected, match="outside target function"):
        scoped_candidate(FIXTURE.encode(), "divide", expected, expected + '\nVERSION = "modified"')


def test_signature_change_is_rejected():
    expected = function_source(FIXTURE, "divide")
    with pytest.raises(PatchRejected, match="signature"):
        scoped_candidate(FIXTURE.encode(), "divide", expected, "def divide(a):\n    return a")


def test_unapproved_call_is_rejected():
    expected = function_source(FIXTURE, "divide")
    with pytest.raises(PatchRejected, match="arithmetic fixture policy"):
        scoped_candidate(FIXTURE.encode(), "divide", expected, "def divide(a, b):\n    return eval('1')")


def test_wrong_expected_bytes_are_rejected():
    with pytest.raises(PatchRejected, match="does not match"):
        scoped_candidate(FIXTURE.encode(), "divide", "def divide(a, b):\n    return 100", "def divide(a, b):\n    return a / b")


def test_patch_preserves_every_outside_byte():
    expected = function_source(FIXTURE, "divide")
    replacement = "def divide(a, b):\n    return a / b"
    updated = scoped_candidate(FIXTURE.encode(), "divide", expected, replacement)
    assert updated == FIXTURE.replace(expected, replacement).encode()


def test_regression_restores_exact_original_bytes(tmp_path: Path):
    (tmp_path / "calculator.py").write_bytes(FIXTURE.encode())
    (tmp_path / "test_calculator.py").write_bytes(FIXTURE_TESTS.encode())
    before = (tmp_path / "calculator.py").read_bytes()
    expected = function_source(FIXTURE, "divide")
    result = try_repair(tmp_path, expected, "def divide(a, b):\n    return 0")
    assert not result["accepted"] and result["original_bytes_restored"]
    assert (tmp_path / "calculator.py").read_bytes() == before


def test_valid_fix_passes_the_fixture_tests(tmp_path: Path):
    (tmp_path / "calculator.py").write_bytes(FIXTURE.encode())
    (tmp_path / "test_calculator.py").write_bytes(FIXTURE_TESTS.encode())
    result = try_repair(tmp_path, function_source(FIXTURE, "divide"), "def divide(a, b):\n    return a / b")
    assert result["accepted"] and result["tests"]["summary"] == "3 passed"
