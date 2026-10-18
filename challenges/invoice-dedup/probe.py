"""The untrusted half of the acceptance suite: it runs inside the isolated container, next to the
submitted source, and reports what the submission's `reconcile` returns for each case's inputs.

It never sees an expected result; the runner compares outside the container. Its answers are the
last stdout line starting with MARK, as JSON: {"answers": {case: {"actual": report} |
{"error": exception type}}} or {"import_error": exception type}.
"""

import json
import sys

MARK = "VERIFIED-PROBE "


def main() -> None:
    cases = json.load(sys.stdin)
    sys.path.insert(0, "/work/src")
    try:
        from reconcile import Invoice, PurchaseOrder, reconcile
    except BaseException as e:  # noqa: BLE001 - the submission's failure to import is the answer
        print(MARK + json.dumps({"import_error": type(e).__name__}))
        return
    answers = {}
    for case in cases:
        try:
            report = reconcile(
                [Invoice.from_dict(d) for d in case["invoices"]],
                [PurchaseOrder.from_dict(d) for d in case["orders"]],
            )
            answers[case["name"]] = {"actual": json.loads(json.dumps(report.as_dict(), default=str))}
        except BaseException as e:  # noqa: BLE001 - a raised exception is that case's answer
            answers[case["name"]] = {"error": type(e).__name__}
    print(MARK + json.dumps({"answers": answers}, ensure_ascii=False))


if __name__ == "__main__":
    main()
