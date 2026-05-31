"""Smoke test the QA backend through HTTP.

Usage:
    python scripts/smoke_test_backend.py --base-url http://127.0.0.1:8000
    python scripts/smoke_test_backend.py --base-url http://127.0.0.1:8000 --include-db

The default mode only checks endpoints that should work without real database
credentials. `--include-db` additionally checks feedback/admin endpoints and
expects the running server to have MYSQL_DSN configured and qa_ tables created.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


@dataclass(slots=True)
class CheckResult:
    name: str
    ok: bool
    detail: str


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--include-db", action="store_true")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    results: list[CheckResult] = []

    results.append(check_health(base_url))
    ask_result, qa_log_id = check_demo_ask(base_url)
    results.append(ask_result)
    results.append(check_context_follow_up(base_url))
    results.append(check_statistics_intent(base_url))

    if args.include_db:
        results.append(check_feedback(base_url, qa_log_id))
        results.append(check_admin_logs(base_url))
        results.append(check_admin_statistics(base_url))

    for result in results:
        prefix = "PASS" if result.ok else "FAIL"
        print(f"[{prefix}] {result.name}: {result.detail}")

    return 0 if all(result.ok for result in results) else 1


def check_health(base_url: str) -> CheckResult:
    status, data = request_json("GET", f"{base_url}/api/health")
    return CheckResult(
        "health",
        status == 200 and data.get("status") == "ok",
        f"status={status}, body={data}",
    )


def check_demo_ask(base_url: str) -> tuple[CheckResult, str | None]:
    payload = {
        "question": "演示文物的材质是什么？",
        "objectId": "DEMO_001",
        "sessionId": "smoke-session",
        "sourceClient": "smoke-test",
    }
    status, data = request_json("POST", f"{base_url}/api/qa/ask", payload)
    ok = (
        status == 200
        and data.get("status") == "answered"
        and data.get("intent") == "artifact_material"
        and data.get("resolvedObject", {}).get("objectId") == "DEMO_001"
    )
    return (
        CheckResult(
            "qa ask demo material",
            ok,
            f"status={status}, qaLogId={data.get('qaLogId')}, intent={data.get('intent')}",
        ),
        data.get("qaLogId") if isinstance(data.get("qaLogId"), str) else None,
    )


def check_context_follow_up(base_url: str) -> CheckResult:
    payload = {
        "question": "它的尺寸是多少？",
        "sessionId": "smoke-session",
        "sourceClient": "smoke-test",
    }
    status, data = request_json("POST", f"{base_url}/api/qa/ask", payload)
    ok = (
        status == 200
        and data.get("intent") == "artifact_dimensions"
        and data.get("resolvedObject", {}).get("objectId") == "DEMO_001"
    )
    return CheckResult(
        "qa context follow-up",
        ok,
        f"status={status}, intent={data.get('intent')}, objectId={data.get('resolvedObject', {}).get('objectId')}",
    )


def check_statistics_intent(base_url: str) -> CheckResult:
    payload = {
        "question": "大英博物馆收藏了多少件中国文物？",
        "sourceClient": "smoke-test",
    }
    status, data = request_json("POST", f"{base_url}/api/qa/ask", payload)
    entities = data.get("debug", {}).get("entities", {})
    ok = (
        status == 200
        and data.get("intent") == "statistics_count"
        and entities.get("museum") == "大英博物馆"
    )
    return CheckResult(
        "qa statistics intent",
        ok,
        f"status={status}, intent={data.get('intent')}, entities={entities}",
    )


def check_feedback(base_url: str, qa_log_id: str | None) -> CheckResult:
    if not qa_log_id:
        return CheckResult("feedback", False, "qaLogId missing from ask response")
    payload = {
        "qaLogId": qa_log_id,
        "feedbackType": "helpful",
        "sourceClient": "smoke-test",
    }
    status, data = request_json("POST", f"{base_url}/api/qa/feedback", payload)
    return CheckResult(
        "feedback",
        status == 200 and data.get("reviewTaskCreated") is False,
        f"status={status}, body={data}",
    )


def check_admin_logs(base_url: str) -> CheckResult:
    query = urlencode({"page": 1, "pageSize": 1})
    status, data = request_json("GET", f"{base_url}/api/admin/qa/logs?{query}")
    return CheckResult(
        "admin logs",
        status == 200 and "items" in data,
        f"status={status}, total={data.get('total')}",
    )


def check_admin_statistics(base_url: str) -> CheckResult:
    status, data = request_json(
        "GET",
        f"{base_url}/api/admin/qa/statistics/inaccurate-types",
    )
    return CheckResult(
        "admin inaccurate statistics",
        status == 200 and isinstance(data, list),
        f"status={status}, rows={len(data) if isinstance(data, list) else 'n/a'}",
    )


def request_json(
    method: str,
    url: str,
    payload: dict[str, Any] | None = None,
) -> tuple[int, Any]:
    body = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"

    request = Request(url, data=body, headers=headers, method=method)
    try:
        with urlopen(request, timeout=10) as response:
            raw = response.read().decode("utf-8")
            return response.status, json.loads(raw) if raw else {}
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            data = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            data = {"raw": raw}
        return exc.code, data
    except URLError as exc:
        return 0, {"error": str(exc.reason)}


if __name__ == "__main__":
    sys.exit(main())
