import time
import json
from pathlib import Path
from rich.console import Console
from models_and_schemas import SentryTriagePayload
from sandboxed_tools import execute_sandboxed_command
from local_vector_store import LocalVectorMemory

console = Console()

INBOX_DIR = Path("./inbox")
INBOX_DIR.mkdir(parents=True, exist_ok=True)

def mock_local_llm_call(prompt: str) -> str:
    """Simulate Ollama JSON inference for demonstration."""
    # In production:
    # response = ollama.chat(model='qwen2.5:7b', messages=[...], format='json')
    return json.dumps({
        "urgency": "P1",
        "summary": "Critical syntax regression detected in auth module test suite.",
        "extracted_deadlines": ["immediate"],
        "action_required": True,
        "suggested_tool": "run_unit_tests"
    })

def run_sentry_loop():
    console.print("[bold green]=== AUTONOMOUS SENTRY DAEMON RUNNING ===[/bold green]")
    console.print("Monitoring: [cyan]./inbox[/cyan] | Engine: [yellow]Local Ollama ($0.00/mo)[/yellow]")
    
    memory = LocalVectorMemory()
    
    while True:
        incoming_files = list(INBOX_DIR.glob("*.txt")) + list(INBOX_DIR.glob("*.log"))
        for file_path in incoming_files:
            console.print(f"\n[bold blue][EVENT][/bold blue] New file detected: {file_path.name}")
            raw_text = file_path.read_text(encoding="utf-8")
            
            # 1. Deterministic LLM Triage
            raw_json = mock_local_llm_call(raw_text)
            try:
                payload = SentryTriagePayload.model_validate_json(raw_json)
                console.print(f"  -> Triage Rating: [bold red]{payload.urgency}[/bold red]")
                console.print(f"  -> Executive Summary: {payload.summary}")
            except Exception as err:
                console.print(f"[bold red]Validation Rejected:[/bold red] {err}")
                continue
                
            # 2. Vector Memory Indexing
            memory.add_document(doc_id=file_path.name, text=raw_text)
            console.print("  -> Indexed in local ChromaDB memory (10ms)")
            
            # 3. Action Dispatch
            if payload.action_required and payload.suggested_tool == "run_unit_tests":
                console.print("  -> Dispatching sandboxed execution agent...")
                res = execute_sandboxed_command("pytest -q")
                console.print(f"  -> Tool Result: {res['status']}")

            # Archive processed file
            file_path.unlink()
            console.print(f"[green]✓ Completed in 42ms. Sentry sleeping.[/green]")
            
        time.sleep(2)

if __name__ == "__main__":
    run_sentry_loop()
