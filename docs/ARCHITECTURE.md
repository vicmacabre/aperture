# Architecture

## The rule that keeps it modular

**Dependencies point inward.** `core.py` holds the domain model and the one function that turns evidence into a verdict. It does no
I/O and imports nothing from the package. Everything that is likely to change (targets, carriers, reporters, the CLI) depends on it, never the reverse.

```
cli ─> engine ─> core <─ oracles          carriers (leaf: pure str -> str)
        │          ^
        ├─> targets ─> http, curl         reporters (leaf: report dict -> text)
        └─> worker (child process)
```

## Ports

| Port | Contract | Built-ins | Add one by |
|---|---|---|---|
| Carrier | `str -> str` plus metadata | 22 | `@carrier(...)` or an entry point |
| Target | `send(probe) -> Observation`, declares `capabilities` | http, pipeline | a class implementing `core.Target` |
| Oracle | `judge(probe, obs) -> evidence dict`, declares what it `requires` | model, stage, guardrail | append to `oracles.ORACLES` |
| Reporter | plain function over the report dict | terminal, html, sarif, json, diff | a function |

The three "modes" (black box, model only, full pipeline) are **not code paths**. They are targets offering different capabilities
(`output`, `trace`). An oracle that needs `trace` is simply skipped on a target that cannot provide it. The engine has no `if mode ==` anywhere.

## One probe's life

1. A carrier encodes the fixed instruction (with a per-probe canary: `HMAC(run secret, carrier, trial)`) into a hidden fragment.
2. The probe text (benign host sentence + fragment) goes to the target. Pipeline targets return the text after every stage.
3. Each oracle reads the observation and returns evidence (`obeyed`, `reached`, `blocked`, per-stage states).
4. `core.verdict` is the **only** place evidence becomes a verdict. Rules are ordered: blocked, obeyed, control-failed, stripped, held, reaches.
5. Trials aggregate to one row per carrier, with a Wilson 95% interval for the exposure rate.

## Reliability decisions

- **Failure isolation:** a probe that throws becomes an error observation. A circuit breaker aborts after consecutive failures.
- **Crash-safe and resumable:** every finished probe is appended to a JSONL file and flushed; `--resume` skips finished probes and reuses the run secret, so canaries still match.
- **Calibration:** the plain-text control probe prevents a weak or refusing model from producing false reassurance.
- **Honest outputs:** no SAFE verdict, confidence intervals, and a standing "lower bound" caveat.
- **Concurrency:** a thread pool bounded by the target (`max_concurrency`) with a global pacer (requests/second). Multi-step targets run one probe at a time because they share server-side state (found by the end-to-end tests).
- **Isolation:** user pipeline code runs in a child process with a per-probe timeout; a hang is killed and the worker restarted.

## Trade-offs

- Stdlib threads instead of asyncio: the workload is a few hundred network calls, and threads keep the code short and dependency-free.
- JSONL instead of SQLite for run state: append-only, crash-safe, greppable, and ten lines of code.
- Verdict rules are one function, not a plugin point, so the meaning of a verdict can never be changed by a stray plugin.
