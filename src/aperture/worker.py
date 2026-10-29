"""Child process for PipelineTarget. Loads STAGES from the user's file and serves JSON lines.
STAGES = [("name", fn), ("guard", fn, "guardrail"), ("llm", fn, "model")]
  transform (default): fn(text) -> text      guardrail: fn(text) -> True if flagged (halts the probe)
  model: fn(text) -> reply text"""

import json
import runpy
import sys
import traceback


def main(path: str) -> None:
    out, sys.stdout = sys.stdout, sys.stderr  # user print() must not corrupt the protocol
    stages = [(s[0], s[1], s[2] if len(s) > 2 else "transform") for s in runpy.run_path(path)["STAGES"]]

    def emit(o: dict) -> None:  # type: ignore[type-arg]
        out.write(json.dumps(o) + "\n")
        out.flush()

    emit({"ready": True, "stages": [[n, role] for n, _, role in stages]})
    for line in sys.stdin:
        text, trace, output, err = json.loads(line)["text"], [], None, None
        try:
            for name, fn, role in stages:
                if role == "guardrail":
                    flagged = bool(fn(text))
                    trace.append({"name": name, "role": role, "text": None, "flagged": flagged})
                    if flagged:
                        break
                elif role == "model":
                    output = str(fn(text))
                    trace.append({"name": name, "role": role, "text": None, "flagged": None})
                else:
                    text = fn(text)
                    trace.append({"name": name, "role": role, "text": text, "flagged": None})
        except Exception:  # noqa: BLE001 - report any stage failure to the engine, keep serving
            err = traceback.format_exc(limit=3)
        emit({"trace": trace, "output": output, "error": err})


if __name__ == "__main__":
    try:
        main(sys.argv[1])
    except Exception:  # noqa: BLE001
        print(json.dumps({"ready": False, "error": traceback.format_exc(limit=3)}), file=sys.__stdout__, flush=True)
