# verified-acceptance

This repository runs [Verified](https://beverified.ai)'s acceptance suites against coding agents' pull requests, in GitHub's disposable runners. Each run executes one exact commit of one submission.

How a run works:
- It is started by hand (`workflow_dispatch`) with a challenge, an attempt and a commit SHA.
- It fetches that commit by SHA, never a branch.
- It runs the challenge's probe on the commit in a container with no network, a read-only root, an unprivileged user and bounded resources, inside the runner's single-use VM.
- It uploads what the submission returned for each input, as the `answers` artifact.

The job has read permission only and holds no secrets. The submitted code is treated as hostile.

What is **not** here:
- **The expected results.** They stay with Verified. Its acceptance observer reads a run (workflow commit, run id, the submission's SHA, the artifact's digest) through GitHub's API and compares the answers with the frozen expectations. The platform then evaluates the challenge's Work Contract.
- **Any verdict.** A run decides nothing.

| Challenge | Submissions | Probe and inputs |
|---|---|---|
| `invoice-dedup` | [`dekrops/invoice-reconciliation`](https://github.com/dekrops/invoice-reconciliation), issue #1 | `challenges/invoice-dedup/` |

`probe.py` is byte-identical to the one frozen in Verified's repository. `inputs.json` holds exactly the inputs of its frozen cases. The observer checks both by digest at the run's workflow commit.

## GitHub tasks

`task.yml` runs any GitHub task frozen in Verified's Playground, with no per-task file here. Verified starts the run (`workflow_dispatch`) with:
- the task, the attempt, the repository and the commit SHA;
- the task's **run bundle** (`verified-suite-run/1`, gzip and base64). It holds the container image (pinned by digest), the command, the probe and the test cases' inputs. It holds no expected result.

The workflow refuses a malformed bundle, fetches the commit by SHA, and runs the probe in the same isolated container. It uploads the `answers` artifact with the bundle's digest (SHA-256 of its exact bytes). Verified's observer checks that digest against the task's frozen suite before comparing anything.

`tooling/task.py` unpacks the bundle and assembles the answers. A run is dispatched with the ref `task-runner-1`, a tag at the reviewed commit the observer pins.
