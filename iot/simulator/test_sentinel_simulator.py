"""Boundary checks for synthetic provenance and device-key transport."""
from contextlib import contextmanager, redirect_stdout, redirect_stderr
from http.server import BaseHTTPRequestHandler, HTTPServer
import argparse
import io
import json
import random
import threading
import unittest
from urllib.error import HTTPError

from sentinel_simulator import main, make_payload, positive_interval, send, valid_url


@contextmanager
def receiver(redirect=False):
    received = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
            received.append((self.path, self.headers.get("X-Device-Key"), json.loads(body)))
            self.send_response(307 if redirect else 201)
            if redirect:
                self.send_header("Location", "/must-not-receive-secret")
            self.end_headers()

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/api/telemetry", received
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)


class SimulatorTests(unittest.TestCase):
    def test_dry_run_is_explicitly_synthetic_and_finite(self):
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            self.assertEqual(main(["--dry-run", "--once"]), 0)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["source"], "simulator")
        self.assertTrue(payload["observed_at"].endswith("Z"))
        self.assertEqual(len(payload["readings"]), 4)
        self.assertIn("sintéticas", stderr.getvalue())

    def test_transport_keeps_key_in_header_and_provenance_in_body(self):
        payload = make_payload("test-device", "Z-001", 0, random.Random(42))
        with receiver() as (url, received):
            self.assertEqual(send(payload, valid_url(url), "unit-test-key"), 201)
        self.assertEqual(received[0][0], "/api/telemetry")
        self.assertEqual(received[0][1], "unit-test-key")
        self.assertEqual(received[0][2]["source"], "simulator")
        self.assertNotIn("unit-test-key", json.dumps(received[0][2]))

    def test_redirect_does_not_forward_device_key(self):
        payload = make_payload("test-device", "Z-001", 0, random.Random(42))
        with receiver(redirect=True) as (url, received):
            with self.assertRaises(HTTPError) as caught:
                send(payload, url, "unit-test-key")
            self.assertEqual(caught.exception.code, 307)
            self.assertEqual(len(received), 1)

    def test_public_http_and_credentials_are_rejected(self):
        for url in (
            "http://example.com/api/telemetry",
            "https://user:password@example.com/api/telemetry",
            "https://example.com/api/telemetry?key=secret",
        ):
            with self.subTest(url=url), self.assertRaises(argparse.ArgumentTypeError):
                valid_url(url)

    def test_interval_rejects_nonfinite_values(self):
        for interval in ("nan", "inf", "0", "-5"):
            with self.subTest(interval=interval), self.assertRaises(argparse.ArgumentTypeError):
                positive_interval(interval)


if __name__ == "__main__":
    unittest.main()
