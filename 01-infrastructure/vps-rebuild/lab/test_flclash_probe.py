import copy
import importlib.util
import json
import pathlib
import socket
import struct
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock

SCRIPT = pathlib.Path(__file__).with_name("flclash_probe.py")
spec = importlib.util.spec_from_file_location("flclash_probe", SCRIPT)
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


def sample_node():
    return {
        "name": "LOCAL-REALITY", "type": "vless", "server": "127.0.0.1",
        "port": 32443, "uuid": "00000000-0000-4000-8000-000000000001",
        "tls": True, "network": "tcp", "flow": "xtls-rprx-vision",
        "udp": True, "servername": "www.example.com", "client-fingerprint": "chrome",
        "reality-opts": {"public-key": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
                         "short-id": "0123456789abcdef", "support-x25519mlkem768": True},
    }


class SafetyTests(unittest.TestCase):
    def test_reconstructs_disabled_network_controls_and_preserves_reality_flag(self):
        raw = {"proxies": [sample_node()], "tun": {"enable": True},
               "dns": {"enable": True}, "listeners": [{"port": 1}],
               "proxy-providers": {"remote": {"url": "https://example.com"}},
               "external-controller": "0.0.0.0:9090"}
        config = probe.sanitize_profile(raw, 28791)
        self.assertTrue(config["proxies"][0]["reality-opts"]["support-x25519mlkem768"])
        self.assertIn("mixed-port", config)
        self.assertEqual(config["mixed-port"], 28791)
        self.assertEqual(config["bind-address"], "127.0.0.1")
        self.assertFalse(config["allow-lan"])
        self.assertFalse(config["tun"]["enable"])
        self.assertFalse(config["tun"]["auto-route"])
        self.assertFalse(config["dns"]["enable"])
        self.assertFalse(config["geo-auto-update"])
        self.assertEqual(config["listeners"], [])
        self.assertEqual(config["proxy-providers"], {})
        self.assertEqual(config["external-controller"], "")
        self.assertEqual(config["rules"], ["MATCH,PROBE"])

    def test_rejects_nonliteral_loopback_and_out_of_lab_port(self):
        for server in ["localhost", "::1", "127.0.0.2", "example.com", "127.0.0.1.example.com"]:
            node = sample_node()
            node["server"] = server
            with self.subTest(server=server), self.assertRaises(ValueError):
                probe.sanitize_profile(node, 28791)
        for port in [443, 31999, 33000, True, "32443"]:
            node = sample_node()
            node["port"] = port
            with self.subTest(port=port), self.assertRaises(ValueError):
                probe.sanitize_profile(node, 28791)

    def test_rejects_file_references_unknown_transports_and_multiple_nodes(self):
        for field in ["certificate", "certificate-file", "private-key", "dialer-proxy", "ws-opts"]:
            node = sample_node()
            node[field] = "/Users/me/private.pem"
            with self.subTest(field=field), self.assertRaises(ValueError):
                probe.sanitize_profile(node, 28791)
        with self.assertRaises(ValueError):
            probe.sanitize_profile({"proxies": [sample_node(), sample_node()]}, 28791)
        node = sample_node()
        node["network"] = "ws"
        with self.assertRaises(ValueError):
            probe.sanitize_profile(node, 28791)

    def test_validates_reality_and_mixed_port_without_mutating_input(self):
        node = sample_node()
        before = copy.deepcopy(node)
        probe.sanitize_profile(node, 28791)
        self.assertEqual(node, before)
        for field, value in [("public-key", "/etc/passwd"), ("short-id", "not-hex"),
                             ("support-x25519mlkem768", "true")]:
            bad = sample_node()
            bad["reality-opts"][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                probe.sanitize_profile(bad, 28791)
        for port in [80, 32443, True]:
            with self.subTest(port=port), self.assertRaises(ValueError):
                probe.sanitize_profile(sample_node(), port)


class FramingTests(unittest.TestCase):
    def test_little_endian_json_frame_handles_fragmented_read(self):
        left, right = socket.socketpair()
        self.addCleanup(left.close)
        self.addCleanup(right.close)
        payload = {"id": "1", "method": "hello", "data": None}
        encoded = json.dumps(payload, separators=(",", ":")).encode()
        wire = struct.pack("<I", len(encoded)) + encoded
        for fragment in [wire[:1], wire[1:3], wire[3:9], wire[9:]]:
            left.sendall(fragment)
        self.assertEqual(probe.read_frame(right), payload)
        probe.write_frame(right, payload)
        self.assertEqual(left.recv(4096), wire)

    def test_rejects_oversized_or_truncated_frames(self):
        for wire in [struct.pack("<I", probe.MAX_FRAME + 1), struct.pack("<I", 5) + b"{}"]:
            left, right = socket.socketpair()
            self.addCleanup(left.close)
            self.addCleanup(right.close)
            left.sendall(wire)
            left.shutdown(socket.SHUT_WR)
            with self.assertRaises((ValueError, EOFError)):
                probe.read_frame(right)


class LifecycleTests(unittest.TestCase):
    def exercise_lifecycle(self, fail_at=None):
        calls = []
        class FakeSession:
            def request(self, method, data=None):
                calls.append((method, data))
                if method == fail_at:
                    raise RuntimeError("injected failure")
                if method == "getConfig":
                    return {"proxies": [sample_node()]}
                if method in ("validateConfig", "setupConfig"):
                    return ""
                return True
        with tempfile.TemporaryDirectory() as tmp:
            config = probe.sanitize_profile(sample_node(), 28791)
            file = pathlib.Path(tmp) / "config.yaml"
            file.write_text(json.dumps(config))
            hook_calls = []
            def hook():
                hook_calls.append("called")
                if fail_at == "hook":
                    raise RuntimeError("hook failure")
                return ["request completed"]
            if fail_at:
                with self.assertRaises(RuntimeError):
                    probe.run_lifecycle(FakeSession(), pathlib.Path(tmp), config, hook)
            else:
                self.assertEqual(probe.run_lifecycle(FakeSession(), pathlib.Path(tmp), config, hook),
                                 ["request completed"])
            self.assertEqual(calls[-2:], [("stopListener", None), ("shutdown", None)])
            return calls, hook_calls

    def test_config_validation_precedes_start_and_cleanup_follows_hook(self):
        calls, hooks = self.exercise_lifecycle()
        self.assertEqual([c[0] for c in calls], ["getConfig", "validateConfig", "initClash",
                         "setupConfig", "startListener", "stopListener", "shutdown"])
        self.assertEqual(hooks, ["called"])
        self.assertEqual(json.loads(calls[2][1])["version"], 2026071102)
        self.assertEqual(json.loads(calls[3][1])["selected-map"], {"PROBE": "LOCAL-REALITY"})

    def test_cleanup_runs_when_setup_or_request_hook_fails(self):
        for failure in ["initClash", "setupConfig", "startListener", "hook"]:
            with self.subTest(failure=failure):
                self.exercise_lifecycle(failure)


class SessionTests(unittest.TestCase):
    def test_slow_fragments_cannot_extend_request_deadline(self):
        left, right = socket.socketpair()
        left.settimeout(1)
        stopped = threading.Event()
        errors = []
        def serve():
            try:
                request = probe.read_frame(left)
                payload = {"id": request["id"], "method": request["method"], "code": 0, "data": True}
                encoded = json.dumps(payload, separators=(",", ":")).encode()
                wire = struct.pack("<I", len(encoded)) + encoded
                for offset in range(0, len(wire), 3):
                    if stopped.wait(0.03):
                        return
                    left.sendall(wire[offset:offset + 3])
            except OSError as error:
                if not stopped.is_set():
                    errors.append(error)
            except Exception as error:
                errors.append(error)
        thread = threading.Thread(target=serve)
        thread.start()
        started = time.monotonic()
        try:
            session = probe.IPCSession(right, lambda event: None, timeout=0.08)
            with self.assertRaises(TimeoutError):
                session.request("startListener")
            self.assertLess(time.monotonic() - started, 0.25)
        finally:
            stopped.set()
            right.close()
            thread.join(1)
            left.close()
        self.assertFalse(thread.is_alive())
        self.assertEqual(errors, [])

    def test_response_decoding_cannot_accept_success_after_deadline(self):
        left, right = socket.socketpair()
        self.addCleanup(left.close)
        self.addCleanup(right.close)
        probe.write_frame(left, {"id": "1", "method": "startListener", "code": 0, "data": True})
        original_loads = json.loads
        def delayed_decode(data):
            time.sleep(0.06)
            return original_loads(data)
        session = probe.IPCSession(right, lambda event: None, timeout=0.03)
        with mock.patch.object(probe.json, "loads", side_effect=delayed_decode):
            with self.assertRaises(TimeoutError):
                session.request("startListener")

    def test_ipc_request_skips_async_event_and_uses_unique_request_ids(self):
        left, right = socket.socketpair()
        self.addCleanup(left.close)
        self.addCleanup(right.close)
        right.settimeout(1)
        events = []
        requests = []
        def serve():
            for _ in range(2):
                try:
                    request = probe.read_frame(left)
                except EOFError:
                    return
                requests.append(request)
                probe.write_frame(left, {"id": "", "method": "message", "code": 0,
                                         "data": {"type": "loaded", "data": "SECRET-NEVER-LOG"}})
                probe.write_frame(left, {"id": request["id"], "method": request["method"],
                                         "code": 0, "data": True})
        thread = threading.Thread(target=serve)
        thread.start()
        session = probe.IPCSession(right, events.append)
        self.assertIs(session.request("startListener"), True)
        self.assertIs(session.request("stopListener"), True)
        thread.join(2)
        self.assertFalse(thread.is_alive())
        self.assertNotEqual(requests[0]["id"], requests[1]["id"])
        self.assertNotIn("SECRET-NEVER-LOG", json.dumps(events))
        self.assertEqual(events[0]["event"], "loaded")

    def test_owned_process_closes_socket_and_terminates_child_that_ignores_eof(self):
        with tempfile.TemporaryDirectory(prefix="fc-test-", dir="/private/tmp") as tmp:
            root = pathlib.Path(tmp)
            fake = root / "fake_core.py"
            fake.write_text("import socket,sys,time\ns=socket.socket(socket.AF_UNIX)\n"
                            "s.connect(sys.argv[1])\nwhile s.recv(4096): pass\ntime.sleep(30)\n")
            with probe.CoreSession(root, [sys.executable, str(fake)], timeout=1) as session:
                self.assertIsNotNone(session.process)
                self.assertIsNone(session.process.poll())
                owned_pid = session.process.pid
            self.assertIsNotNone(session.process.poll())
            self.assertFalse((root / "core.sock").exists())
            self.assertEqual((root / "core-output.log").stat().st_mode & 0o777, 0o600)
            self.assertGreater(owned_pid, 0)


class RequestTests(unittest.TestCase):
    def test_rejects_urls_with_other_protocols_or_credentials(self):
        for url in ["http://example.com", "file:///etc/passwd", "https://user:pass@example.com",
                    "https:///missing-host", "https://example.com/\nsecret"]:
            with self.subTest(url=url), self.assertRaises(ValueError):
                probe.validate_url(url)
        self.assertEqual(probe.validate_url("https://www.gstatic.com/generate_204"),
                         "https://www.gstatic.com/generate_204")

    def test_curl_uses_explicit_loopback_proxy_and_records_transfer_metrics(self):
        with tempfile.TemporaryDirectory(prefix="fc-curl-", dir="/private/tmp") as tmp:
            fake = pathlib.Path(tmp) / "curl"
            fake.write_text("#!/usr/bin/env python3\nimport json,sys,os\n"
                            "assert sys.argv[1] == '-q', 'user curlrc must be disabled before other options'\n"
                            "assert sys.argv[sys.argv.index('--proxy')+1] == 'http://127.0.0.1:28791'\n"
                            "assert sys.argv[sys.argv.index('--noproxy')+1] == ''\n"
                            "assert sys.argv[sys.argv.index('--proto')+1] == '=https'\n"
                            "assert not any(k.lower() == 'https_proxy' for k in os.environ)\n"
                            "print('204\\t1048576\\t0.25')\n")
            fake.chmod(0o700)
            result = probe.run_curl("https://www.gstatic.com/generate_204", 28791, 10, str(fake))
            self.assertEqual(result["curl_exit"], 0)
            self.assertIn("http_status", result)
            self.assertEqual(result["http_status"], 204)
            self.assertEqual(result["bytes_downloaded"], 1048576)
            self.assertEqual(result["seconds"], 0.25)

    def test_curl_failure_does_not_claim_https_success(self):
        with tempfile.TemporaryDirectory(prefix="fc-curl-", dir="/private/tmp") as tmp:
            fake = pathlib.Path(tmp) / "curl"
            fake.write_text("#!/bin/sh\nprintf '000\\t0\\t0.10\\n'\nexit 35\n")
            fake.chmod(0o700)
            result = probe.run_curl("https://example.com", 28791, 10, str(fake))
            self.assertFalse(result["ok"])
            self.assertEqual(result["curl_exit"], 35)

    def test_probe_rejects_nonloopback_profile_before_starting_child(self):
        with tempfile.TemporaryDirectory() as tmp:
            file = pathlib.Path(tmp) / "bad.json"
            node = sample_node()
            node["server"] = "example.com"
            file.write_text(json.dumps(node))
            with self.assertRaises(ValueError):
                probe.run_probe(file, 28791, [], core_command=["/nonexistent-core"])

    def test_cli_passes_multiple_https_targets_and_preserves_no_request_smoke(self):
        args = probe.parse_args(["--config", "/private/tmp/lab.json", "--port", "28791",
                                 "--url", "https://example.com/a", "--url", "https://example.com/b"])
        self.assertEqual(args.url, ["https://example.com/a", "https://example.com/b"])
        self.assertEqual(probe.parse_args(["--config", "/private/tmp/lab.json"]).url, [])

    def test_startup_timeout_cleans_socket_and_child(self):
        with tempfile.TemporaryDirectory(prefix="fc-test-", dir="/private/tmp") as tmp:
            root = pathlib.Path(tmp)
            session = probe.CoreSession(root, [sys.executable, "-c", "import time; time.sleep(30)"],
                                        timeout=0.1)
            with self.assertRaises(TimeoutError):
                with session:
                    self.fail("unconnected child must not become ready")
            self.assertIsNotNone(session.process.poll())
            self.assertFalse((root / "core.sock").exists())


if __name__ == "__main__":
    unittest.main()
