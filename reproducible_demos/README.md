# Reproducible CPU agent demonstrations

These independently authored examples demonstrate explicit control flow,
validation, and reversible edits using small deterministic fixtures. Existing
repository code is preserved. This folder's MIT license applies only to the new
code and documentation in this folder, not to other repository files or
third-party dependencies.

## Requirements and commands

Use Python 3.10 or newer, Git on `PATH`, and the dependencies listed in
`requirements.txt`. From the repository root:

```sh
cd reproducible_demos
python -m pip install -r requirements.txt
python run_demos.py
python -m pytest -q test_companion.py
```

The demonstrations and tests do not require Ollama, model weights, a GPU,
credentials, or an external service. If the dependencies are already installed,
skip the installation command. The runner creates and removes its own temporary
Git fixture. It creates no commits and does not use reset or checkout.

## What the examples establish

1. **Explicit states and authorization** (`state_machine.py`): a registered-tool
   allowlist accepts an arithmetic tool, rejects schema-invalid triage before
   execution, and rejects an unknown tool. The triage response is a deterministic
   fixture. No LLM routed a task.
2. **Three validation layers** (`structured_output.py`): JSON syntax, Pydantic
   structure/types, and an example business policy have separate outcomes.
   Syntactically valid JSON can fail the schema; schema-valid JSON can fail the
   semantic policy. `build_ollama_request` puts the actual JSON Schema in
   `format` and sets `stream: false`.
3. **Scoped, reversible repair** (`scoped_repair.py`): pytest really fails in
   a temporary fixture, a controlled patch to one arithmetic function passes
   those tests, and a regression candidate is rejected with exact pre-attempt
   bytes restored. An attempted edit outside that function is rejected.
   Candidate patches are deterministic fixtures; no LLM generated them.

The optional `call_local_ollama` function connects only to
`127.0.0.1:11434`. It was **not called or integration-tested** in these CPU runs.
Schema adherence is not proof of factual correctness or task success; an actual
integration still needs semantic checks and explicit acceptance criteria.

## Evidence and limits

`demo_results.json` records the executed runtime versions, disclosures, and 12
presentation steps. Each step has `id`, `title`, `command`, `output`, `before`,
and `after`. It includes no machine-specific filesystem paths. Generated samples
in `samples/` contain fixture inputs, output verdicts, an unexecuted Ollama
request, and the repair source/tests/patches.

The companion test suite has 12 behavioral tests. It checks authorization,
validation layers, AST boundaries, preservation of surrounding bytes, and actual
rollback on a failed fixture test. Passing these tests establishes the behavior
of these fixtures only. It does not establish production reliability, model
reasoning quality, absence of all regressions, overnight operation, latency
benefits, or framework comparisons. Project tests are not a security sandbox;
the arithmetic AST policy here is deliberately narrow. No daemon, automatic
commit, or model benchmark is demonstrated.

Primary references: [Ollama structured outputs](https://docs.ollama.com/capabilities/structured-outputs),
[Ollama chat API](https://docs.ollama.com/api/chat), and
[llama.cpp grammar support and limitations](https://github.com/ggml-org/llama.cpp/blob/master/grammars/README.md).
