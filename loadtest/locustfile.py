"""
Load test for the Sentinel-FFT2EA API.

Two user classes model two different real usage patterns rather than
treating every endpoint as equivalent load:

- SentinelOperatorUser: what an operator dashboard actually does —
  poll /tracks, check /health, occasionally toggle EW, occasionally try
  to acknowledge a TARGET-stage track (best-effort, since which tracks
  are in TARGET at any moment is nondeterministic under concurrent load).

- SentinelDashboardStreamUser: opens the SSE stream and reads a handful
  of live events before disconnecting — models the cost of holding open
  streaming connections separately from the request/response polling
  load above, since these have very different server-side costs.

Run:
    locust -f loadtest/locustfile.py --host http://localhost:8000

Headless (used to produce the numbers in loadtest/README.md):
    locust -f loadtest/locustfile.py --host http://localhost:8000 \
        --headless -u 100 -r 20 -t 60s --csv loadtest/results/run
"""

import random

from locust import HttpUser, between, task

SOURCE_TYPES = ["vehicle_ir", "uav_uas", "elint", "legacy_c2"]


class SentinelOperatorUser(HttpUser):
    weight = 3
    wait_time = between(0.5, 2.0)

    @task(6)
    def list_tracks(self):
        self.client.get("/tracks", name="/tracks")

    @task(3)
    def health_check(self):
        self.client.get("/health", name="/health")

    @task(2)
    def toggle_ew(self):
        source = random.choice(SOURCE_TYPES)
        self.client.post(f"/ew/toggle?source_type={source}", name="/ew/toggle")

    @task(2)
    def attempt_acknowledge(self):
        resp = self.client.get("/tracks", name="/tracks [pre-ack scan]")
        try:
            tracks = resp.json()
        except ValueError:
            return

        target_tracks = [t for t in tracks if t.get("stage") == "target"]
        if not target_tracks:
            return

        track_id = random.choice(target_tracks)["track_id"]
        with self.client.post(
            f"/tracks/{track_id}/ack", name="/tracks/[id]/ack", catch_response=True
        ) as r:
            # 400 is expected here under concurrent load: another simulated
            # operator may have already acknowledged the same track between
            # our scan and our POST. That's a real race, not a bug — treat
            # it as success for load-test purposes rather than masking it
            # entirely, since a 5xx would still fail correctly below.
            if r.status_code in (200, 400):
                r.success()


class SentinelDashboardStreamUser(HttpUser):
    weight = 1
    wait_time = between(3, 8)

    @task
    def open_stream_and_read_events(self):
        with self.client.get(
            "/stream/tracks", name="/stream/tracks", stream=True, catch_response=True
        ) as resp:
            try:
                lines_read = 0
                for _ in resp.iter_lines():
                    lines_read += 1
                    if lines_read >= 6:  # a couple of full SSE event/data pairs
                        break
                resp.success()
            except Exception as e:
                resp.failure(str(e))
