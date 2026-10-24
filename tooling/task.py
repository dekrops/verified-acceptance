"""A GitHub task's acceptance run: unpacks the run's bundle, and assembles the answers document.

    python3 tooling/task.py unpack DIR        reads the bundle from $BUNDLE (gzip, base64)
    python3 tooling/task.py answers DIR TASK ATTEMPT REPOSITORY HEAD TREE STATUS PROBE_OUTPUT

A bundle is what Verified sends for one task (profile verified-suite-run/1): the container image,
pinned by digest; the command; the probe, a small program that runs the submitted code on each
input and prints what it returned; and the test cases' inputs. It holds no expected result.
Verified's acceptance observer checks the bundle by its digest against the task's frozen suite,
and compares the answers with the expectations it keeps.
"""

import base64
import gzip
import hashlib
import io
import json
import os
import pathlib
import re
import sys

MARK = "VERIFIED-PROBE "
IMAGE = re.compile(r"^[a-z0-9][a-z0-9._/:-]{0,200}@sha256:[0-9a-f]{64}$")
PROBE = re.compile(r"^[A-Za-z0-9_-]{1,40}\.[a-z0-9]{1,5}$")
CASE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")


def fail(message: str) -> None:
    print(f"refused: {message}", file=sys.stderr)
    sys.exit(1)


def unpack(out: pathlib.Path) -> None:
    packed = os.environ.get("BUNDLE", "")
    if not packed or len(packed) > 60000:
        fail("the bundle is missing or too large")
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(base64.b64decode(packed, validate=True))) as z:
            raw = z.read((1 << 20) + 1)
    except Exception:  # noqa: BLE001 - any malformed bundle is refused alike
        fail("the bundle is not gzip in base64")
    if len(raw) > 1 << 20:
        fail("the bundle is larger than 1 MiB")
    try:
        b = json.loads(raw)
    except ValueError:
        fail("the bundle is not JSON")
    if b.get("profile") != "verified-suite-run/1":
        fail("not a verified-suite-run/1 bundle")
    if not isinstance(b.get("environment"), str) or not IMAGE.match(b["environment"]):
        fail("the image is not pinned by digest")
    command = b.get("command")
    if (not isinstance(command, list) or not 1 <= len(command) <= 8
            or not all(isinstance(a, str) and 0 < len(a) <= 200 and "\0" not in a for a in command)):
        fail("the command is not 1 to 8 arguments")
    probe = b.get("probe") or {}
    if not isinstance(probe.get("name"), str) or not PROBE.match(probe["name"]) or not isinstance(probe.get("text"), str):
        fail("the probe is malformed")
    inputs = b.get("inputs")
    if not isinstance(inputs, list) or not all(
            isinstance(i, dict) and set(i) == {"name", "input"} and isinstance(i["name"], str)
            and CASE.match(i["name"]) for i in inputs):
        fail("the inputs are malformed")
    out.mkdir(parents=True)
    (out / "probe").mkdir()
    (out / "probe" / probe["name"]).write_text(probe["text"], encoding="utf-8")
    (out / "inputs.json").write_text(json.dumps(inputs, ensure_ascii=False), encoding="utf-8")
    (out / "command").write_bytes(b"".join(a.encode() + b"\0" for a in command))
    (out / "image").write_text(b["environment"])
    (out / "probe-name").write_text(probe["name"])
    (out / "digest").write_text("sha-256:" + hashlib.sha256(raw).hexdigest())


def answers(run: pathlib.Path, task, attempt, repository, head, tree, status, output) -> None:
    with open(output, "rb") as f:
        text = f.read(4 << 20).decode("utf-8", errors="replace")
    lines = [l for l in text.splitlines() if l.startswith(MARK)]
    doc = {
        "profile": "github-task-answers/1",
        "task": task,
        "attempt": attempt,
        "repository": repository,
        "headSha": head,
        "treeSha": tree,
        "environment": (run / "image").read_text(),
        "bundle": (run / "digest").read_text(),
    }
    if status == "timed-out":
        doc["outcome"] = "timed-out"
    elif not lines:
        doc["outcome"] = "no-answer"
    else:
        try:
            doc["answers"] = json.loads(lines[-1][len(MARK):])
            doc["outcome"] = "answered"
        except ValueError:
            doc["outcome"] = "no-answer"
    with open("answers.json", "w", encoding="utf-8") as f:
        json.dump(doc, f, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    print(json.dumps({k: doc[k] for k in ("task", "attempt", "headSha", "treeSha", "bundle", "outcome")}))


if __name__ == "__main__":
    if sys.argv[1:2] == ["unpack"]:
        unpack(pathlib.Path(sys.argv[2]))
    elif sys.argv[1:2] == ["answers"]:
        answers(pathlib.Path(sys.argv[2]), *sys.argv[3:])
    else:
        fail(__doc__)
