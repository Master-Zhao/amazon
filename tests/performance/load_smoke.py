"""Dependency-free, read-only HTTP load smoke runner for repeatable M6 checks."""

from __future__ import annotations

import argparse
import json
import math
import statistics
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor


def percentile(values: list[float], percentile_value: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, math.ceil(percentile_value * len(ordered)) - 1)
    return round(ordered[index], 2)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run a bounded, read-only HTTP load smoke test."
    )
    parser.add_argument("--base-url", default="http://localhost:8081")
    parser.add_argument("--path", default="/health/live")
    parser.add_argument("--duration", type=int, default=30)
    parser.add_argument("--rps", type=int, default=10)
    parser.add_argument("--workers", type=int, default=20)
    parser.add_argument("--timeout", type=float, default=5.0)
    parser.add_argument("--access-token")
    parser.add_argument("--tenant-id")
    args = parser.parse_args()

    if args.duration < 1 or args.rps < 1 or args.workers < 1:
        parser.error("duration, rps and workers must be positive")

    url = f"{args.base_url.rstrip('/')}/{args.path.lstrip('/')}"
    headers = {"Accept": "application/json", "User-Agent": "amazon-ads-m6-load-smoke"}
    if args.access_token:
        headers["Authorization"] = f"Bearer {args.access_token}"
    if args.tenant_id:
        headers["X-Tenant-ID"] = args.tenant_id

    latencies: list[float] = []
    statuses: dict[str, int] = {}
    lock = threading.Lock()

    def request_once() -> None:
        started = time.perf_counter()
        status = "NETWORK_ERROR"
        try:
            request = urllib.request.Request(url, headers=headers, method="GET")
            with urllib.request.urlopen(request, timeout=args.timeout) as response:
                response.read()
                status = str(response.status)
        except urllib.error.HTTPError as error:
            error.read()
            status = str(error.code)
        except (OSError, TimeoutError):
            pass
        elapsed_ms = (time.perf_counter() - started) * 1000
        with lock:
            latencies.append(elapsed_ms)
            statuses[status] = statuses.get(status, 0) + 1

    started = time.perf_counter()
    deadline = started + args.duration
    interval = 1 / args.rps
    submitted = 0
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        next_request = started
        while time.perf_counter() < deadline:
            executor.submit(request_once)
            submitted += 1
            next_request += interval
            wait_for = next_request - time.perf_counter()
            if wait_for > 0:
                time.sleep(wait_for)

    elapsed = time.perf_counter() - started
    success_count = sum(
        count for status, count in statuses.items() if status.startswith("2")
    )
    result = {
        "url": url,
        "durationSeconds": round(elapsed, 2),
        "targetRps": args.rps,
        "submitted": submitted,
        "completed": len(latencies),
        "successful": success_count,
        "statuses": statuses,
        "observedRps": round(len(latencies) / elapsed, 2),
        "latencyMs": {
            "mean": round(statistics.fmean(latencies), 2) if latencies else None,
            "p50": percentile(latencies, 0.50),
            "p95": percentile(latencies, 0.95),
            "max": round(max(latencies), 2) if latencies else None,
        },
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if success_count == len(latencies) and latencies else 1


if __name__ == "__main__":
    raise SystemExit(main())
