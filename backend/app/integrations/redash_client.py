"""Redash API client — mirrors the same integration pattern already proven in
the Milestone-Dostt sibling app's services/redash.js: POST a query run, either
get a cached result back immediately or poll the async job, then fetch the
result rows. Query ids for our four validated queries (recent calls, recent
recharges, recent withdrawals, support-issue catalog — built and tested
against real data on 2026-09-08) live in app/core/config.py.

Callers gate on MOCK_MODE before calling this, same convention as every other
file in app/integrations/ — this module doesn't know or care about MOCK_MODE
itself, it just raises if the two env vars it needs aren't set.
"""

import time

import httpx

from app.core.config import settings

POLL_INTERVAL_SEC = 2
POLL_TIMEOUT_SEC = 120

_JOB_SUCCESS = 3
_JOB_FAILED = 4
_JOB_CANCELLED = 5


class RedashNotConfiguredError(RuntimeError):
    pass


class RedashQueryError(RuntimeError):
    pass


def _client() -> httpx.Client:
    return httpx.Client(
        base_url=settings.REDASH_BASE_URL,
        headers={"Authorization": f"Key {settings.REDASH_API_KEY}"},
        timeout=30.0,
    )


def _poll_job(client: httpx.Client, job_id: str) -> int:
    deadline = time.monotonic() + POLL_TIMEOUT_SEC
    while time.monotonic() < deadline:
        resp = client.get(f"/api/jobs/{job_id}")
        resp.raise_for_status()
        job = resp.json()["job"]
        status = job["status"]
        if status == _JOB_SUCCESS:
            return job["query_result_id"]
        if status == _JOB_FAILED:
            raise RedashQueryError(f"Redash job failed: {job.get('error')}")
        if status == _JOB_CANCELLED:
            raise RedashQueryError("Redash job was cancelled")
        time.sleep(POLL_INTERVAL_SEC)
    raise RedashQueryError(f"Redash job {job_id} timed out after {POLL_TIMEOUT_SEC}s")


def run_query(query_id: int, params: dict | None = None, max_age: int = 1800) -> list[dict]:
    """Run a saved Redash query and return its result rows as a list of dicts.

    max_age is Redash's own cache TTL in seconds (0 = always fresh, forces a
    live BigQuery run) — matches the parameter Milestone-Dostt's runQuery
    exposes, so the same latency/freshness tradeoff applies here.
    """
    if not settings.REDASH_BASE_URL or not settings.REDASH_API_KEY:
        raise RedashNotConfiguredError("REDASH_BASE_URL/REDASH_API_KEY not set — see .env.example")

    body: dict = {"max_age": max_age}
    if params:
        body["parameters"] = params

    with _client() as client:
        resp = client.post(f"/api/queries/{query_id}/results", json=body)
        resp.raise_for_status()
        data = resp.json()

        if "query_result" in data:
            return data["query_result"]["data"]["rows"]

        if "job" in data:
            result_id = _poll_job(client, data["job"]["id"])
            resp = client.get(f"/api/query_results/{result_id}.json")
            resp.raise_for_status()
            return resp.json()["query_result"]["data"]["rows"]

    raise RedashQueryError("Unexpected Redash response shape")
