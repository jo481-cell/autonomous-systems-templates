# Autonomous Workday — Companion Examples

Educational Python examples accompanying the [Autonomous Workday](https://www.youtube.com/@AutonomousWorkday) series on local AI architecture, structured validation, and automation.

**This repository is a partial teaching scaffold. It is not a complete five-agent system, a measured live bug-fixing demonstration, or production-ready software.** The Python files are preserved from the original companion folder; this README describes their actual implementation and limitations.

## What is included

| File | Current implementation |
|---|---|
| `models_and_schemas.py` | Pydantic models for triage payloads and execution results. |
| `daemon_sentry.py` | Polls an `inbox` folder for text/log files, validates a fixed mock response, indexes the input, invokes `pytest -q`, and deletes each processed input file. |
| `local_vector_store.py` | A small ChromaDB persistence, insertion, and search wrapper using its default embedding function. |
| `sandboxed_tools.py` | File-reading and command-execution examples with a string-prefix allowlist. This is not an operating-system sandbox. |
| `requirements.txt` | The original dependency list; versions are not locked and the complete runtime has not been validated for this publication. |

## Mocked or not implemented

- `mock_local_llm_call()` returns the same hard-coded JSON for every input. It does not call Ollama. The presence of Ollama in the requirements or console labels does not change this.
- No Builder/Critic pair, autonomous bug repair, generated Git diff, complete five-layer orchestration, cloud escalation, or final human approval interface is implemented here.
- The console messages containing `10ms` and `42ms`, and the insertion docstring mentioning a duration, are hard-coded illustrative text. They are not benchmark measurements. This repository does not substantiate a live workflow completed in 42 seconds or a tokens-per-second claim.
- ChromaDB uses its default embedding function; these examples do not configure BGE or Nomic, implement semantic chunking, or integrate retrieval into the daemon's decision loop.

## Before running or adapting the examples

Read the code first and use a disposable, isolated environment containing only throwaway input files.

- `daemon_sentry.py` permanently removes processed input files with `unlink()`. It does not archive them or ask for approval.
- `sandboxed_tools.py` passes an accepted command string to a shell with `shell=True`. Checking a command prefix does not securely constrain shell syntax. Do not pass untrusted or model-generated commands to this helper.
- File reads are not confined to a workspace root. There is no filesystem or process isolation supplied by this repository.
- Running tests executes the code under test. The examples provide no containment for it.
- Pydantic validates the declared schema; it does not prove that a model's output is correct or safe. The summary field limits characters, not words.
- The daemon invokes `pytest`, which is not included in `requirements.txt`. Dependency and ChromaDB API compatibility require review before execution; no successful end-to-end run is claimed.

Local execution alone does not establish complete privacy, zero operating costs, a guaranteed latency, or reliable autonomous operation. Those properties depend on the implementation and environment.

## Get the source

```bash
git clone https://github.com/jo481-cell/autonomous-systems-templates.git
cd autonomous-systems-templates
```

The intended reading order is `models_and_schemas.py`, `local_vector_store.py`, `sandboxed_tools.py`, and then `daemon_sentry.py`. Review and replace the mock and unsafe execution boundaries before adapting this scaffold to real tasks. No model downloads or software execution are required to read the examples.

## Relation to the videos

The series discusses a broader architecture than these files implement. Treat diagrams, proposed workflows, and numerical illustrations separately from implemented functionality and measured results. The source files are provided so viewers can inspect the examples rather than infer that a complete deployed system is included.

## License note

The supplied companion README stated "MIT License. Free to use, adapt, and build upon." No separate `LICENSE` file was included in that folder. This publication preserves that statement and does not add a new license file.
