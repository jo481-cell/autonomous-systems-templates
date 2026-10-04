"""AST-scoped, reversible patches in a controlled temporary fixture.

Only the fixture's named function can change. Candidate bodies are limited
to a small arithmetic AST allowlist. Running project tests is not a sandbox.
"""
from __future__ import annotations

import ast
import os
import re
import subprocess
import sys
from pathlib import Path


class PatchRejected(ValueError):
    pass


ALLOWED_NODES = (
    ast.Module, ast.FunctionDef, ast.arguments, ast.arg, ast.Return,
    ast.BinOp, ast.Name, ast.Load, ast.Constant, ast.Add, ast.Sub,
    ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow, ast.USub, ast.UAdd,
    ast.UnaryOp, ast.Expr,
)


def function_source(source: str, name: str) -> str:
    matches = [node for node in ast.parse(source).body if isinstance(node, ast.FunctionDef) and node.name == name]
    if len(matches) != 1:
        raise PatchRejected("target function must exist exactly once")
    return ast.get_source_segment(source, matches[0])


def scoped_candidate(original: bytes, function_name: str, expected: str, replacement: str) -> bytes:
    """Construct a candidate preserving every byte outside one function."""
    source = original.decode("utf-8")
    tree = ast.parse(source)
    functions = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == function_name]
    if len(functions) != 1:
        raise PatchRejected("target function must exist exactly once")
    target = functions[0]
    if target.decorator_list:
        raise PatchRejected("decorated functions are outside this fixture's scope")
    if ast.get_source_segment(source, target) != expected:
        raise PatchRejected("original function does not match")
    try:
        patch_tree = ast.parse(replacement)
    except SyntaxError as exc:
        raise PatchRejected("invalid replacement syntax") from exc
    if len(patch_tree.body) != 1 or not isinstance(patch_tree.body[0], ast.FunctionDef):
        raise PatchRejected("edits outside target function")
    candidate = patch_tree.body[0]
    if candidate.name != function_name or ast.dump(candidate.args) != ast.dump(target.args):
        raise PatchRejected("function name and signature must be preserved")
    if candidate.decorator_list or candidate.returns or getattr(candidate, "type_params", []):
        raise PatchRejected("decorators, annotations and type parameters are outside fixture scope")
    if any(not isinstance(node, ALLOWED_NODES) for node in ast.walk(patch_tree)):
        raise PatchRejected("replacement exceeds arithmetic fixture policy")
    # AST columns are UTF-8 byte offsets, so preserve the surrounding bytes.
    lines = original.splitlines(keepends=True)
    begin = sum(map(len, lines[:target.lineno - 1])) + target.col_offset
    end = sum(map(len, lines[:target.end_lineno - 1])) + target.end_col_offset
    updated = original[:begin] + replacement.encode("utf-8") + original[end:]
    ast.parse(updated.decode("utf-8"))
    return updated


def run_pytest(workspace: Path, python: str = sys.executable) -> dict:
    env = dict(os.environ, PYTEST_DISABLE_PLUGIN_AUTOLOAD="1", PYTHONDONTWRITEBYTECODE="1")
    process = subprocess.run(
        [python, "-m", "pytest", "-q", "--tb=short", "test_calculator.py"],
        cwd=workspace, env=env, capture_output=True, text=True, timeout=20,
    )
    output = process.stdout + process.stderr
    summary = re.search(r"(\d+ failed, \d+ passed|\d+ passed|\d+ failed) in", output)
    return {"passed": process.returncode == 0, "return_code": process.returncode,
            "summary": summary.group(1) if summary else "test execution error", "output": output}


def try_repair(workspace: Path, expected: str, replacement: str, python: str = sys.executable) -> dict:
    """One attempt; restore exact pre-attempt bytes on rejection/error.

    The workspace and target file are selected by code, never by model output.
    No commit, reset, network access, or existing user checkout is involved.
    """
    target = workspace.resolve() / "calculator.py"
    if target.is_symlink():
        raise PatchRejected("symlink target is prohibited")
    original = target.read_bytes()
    accepted = False
    result = {}
    try:
        candidate = scoped_candidate(original, "divide", expected, replacement)
        target.write_bytes(candidate)
        tests = run_pytest(workspace, python)
        accepted = tests["passed"]
        result = {"accepted": accepted, "tests": tests}
    finally:
        if not accepted:
            target.write_bytes(original)
    result["original_bytes_restored"] = target.read_bytes() == original if not accepted else None
    return result
