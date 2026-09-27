import subprocess
from pathlib import Path
from typing import Dict, Any

ALLOWED_COMMAND_PREFIXES = [
    "git status",
    "git diff",
    "git log",
    "pytest",
    "python -m unittest",
    "ruff check",
    "black --check"
]

def read_workspace_file(file_path: str, max_chars: int = 4000) -> Dict[str, Any]:
    """Safely inspect a local workspace file with length constraint."""
    p = Path(file_path)
    if not p.exists() or not p.is_file():
        return {"status": "error", "message": f"File {file_path} not found"}
    try:
        content = p.read_text(encoding="utf-8")[:max_chars]
        return {"status": "success", "content": content, "truncated": len(content) >= max_chars}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def execute_sandboxed_command(cmd: str, cwd: str = ".") -> Dict[str, Any]:
    """Execute whitelisted, non-destructive terminal command."""
    is_whitelisted = any(cmd.strip().startswith(prefix) for prefix in ALLOWED_COMMAND_PREFIXES)
    if not is_whitelisted:
        return {
            "status": "blocked_requires_override",
            "message": f"Command '{cmd}' is not in the deterministic whitelist. Explicit human override required."
        }
    try:
        res = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True, timeout=30)
        return {
            "status": "success" if res.returncode == 0 else "failure",
            "exit_code": res.returncode,
            "stdout": res.stdout[:2000],
            "stderr": res.stderr[:1000]
        }
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "message": "Command timed out after 30 seconds"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
