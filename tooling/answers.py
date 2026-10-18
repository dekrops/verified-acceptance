"""Assembles a run's answers document from the probe's output: what was run, on what, and what the
submission returned for each input. It holds no expected result and decides nothing: Verified's
acceptance observer compares the answers with the challenge's frozen expectations.

    python3 tooling/answers.py CHALLENGE ATTEMPT REPOSITORY HEAD TREE IMAGE STATUS PROBE_OUTPUT
"""

import hashlib
import json
import sys

MARK = "VERIFIED-PROBE "


def main(challenge, attempt, repository, head, tree, image, status, output) -> None:
    inputs = open(f"challenges/{challenge}/inputs.json", "rb").read()
    probe = open(f"challenges/{challenge}/probe.py", "rb").read()
    lines = [l for l in open(output, encoding="utf-8", errors="replace").read().splitlines()
             if l.startswith(MARK)]
    doc = {
        "profile": "github-acceptance-answers/1",
        "challenge": challenge,
        "attempt": attempt,
        "repository": repository,
        "headSha": head,
        "treeSha": tree,
        "environment": image,
        "probe": "sha-256:" + hashlib.sha256(probe).hexdigest(),
        "inputs": "sha-256:" + hashlib.sha256(inputs).hexdigest(),
    }
    if status == "timed-out":
        doc["outcome"] = "timed-out"
    elif not lines:
        doc["outcome"] = "no-answer"
    else:
        doc["outcome"] = "answered"
        doc["answers"] = json.loads(lines[-1][len(MARK):])
    with open("answers.json", "w", encoding="utf-8") as f:
        json.dump(doc, f, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    print(json.dumps({k: doc[k] for k in ("attempt", "headSha", "treeSha", "outcome")}))


if __name__ == "__main__":
    main(*sys.argv[1:])
