"""Use an installed FlClash core in a private, loopback-only lab profile.

IPC matches chen08209/FlClash tag v0.8.94 core/server.go and action.go.
This does not invoke the FlClash app or change its profile or OS proxy settings.
"""
import argparse
import base64
import copy
import json
import os
from pathlib import Path
import re
import socket
import struct
import subprocess
import tempfile
import time
import uuid
from urllib.parse import urlsplit

MAX_FRAME = 1024 * 1024
CORE_VERSION = 2026071102
TEST_URL = "https://www.gstatic.com/generate_204"
DEFAULT_CORE = "/Applications/FlClash.app/Contents/MacOS/FlClashCore"


def sanitize_profile(payload, mixed_port):
    if not isinstance(payload, dict):
        raise ValueError("profile must be an object")
    if type(mixed_port) is not int or not 20000 <= mixed_port <= 31999:
        raise ValueError("mixed port must be in 20000–31999")
    nodes = payload.get("proxies", [payload])
    if not isinstance(nodes, list) or len(nodes) != 1 or not isinstance(nodes[0], dict):
        raise ValueError("profile must contain exactly one node")
    node = copy.deepcopy(nodes[0])
    allowed = {"name", "type", "server", "port", "uuid", "tls", "udp", "flow", "network",
               "servername", "client-fingerprint", "packet-encoding", "reality-opts"}
    if set(node) - allowed:
        raise ValueError("node contains unsupported fields or file references")
    if node.get("type") != "vless" or node.get("server") != "127.0.0.1":
        raise ValueError("only literal 127.0.0.1 VLESS nodes are allowed")
    if type(node.get("port")) is not int or not 32000 <= node["port"] <= 32999:
        raise ValueError("node port must be in 32000–32999")
    if node.get("tls") is not True or node.get("network", "tcp") != "tcp":
        raise ValueError("only TCP Reality with TLS enabled is allowed")
    if node.get("flow", "xtls-rprx-vision") not in ("", "xtls-rprx-vision"):
        raise ValueError("unsupported VLESS flow")
    if "udp" in node and type(node["udp"]) is not bool:
        raise ValueError("udp must be boolean")
    if "packet-encoding" in node and node["packet-encoding"] not in ("xudp", "packetaddr"):
        raise ValueError("unsupported packet encoding")
    try:
        if not isinstance(node.get("uuid"), str):
            raise ValueError
        node["uuid"] = str(uuid.UUID(node["uuid"]))
    except ValueError:
        raise ValueError("node uuid is invalid") from None
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,64}", node.get("name", "")):
        raise ValueError("node name must be a short lab identifier")
    servername = node.get("servername", "")
    if not isinstance(servername, str) or not re.fullmatch(r"[A-Za-z0-9.-]{1,253}", servername):
        raise ValueError("servername must be a DNS name")
    if node.get("client-fingerprint", "chrome") not in {
        "chrome", "firefox", "safari", "ios", "android", "edge", "random", "randomized"
    }:
        raise ValueError("unsupported client fingerprint")
    reality = node.get("reality-opts")
    if not isinstance(reality, dict) or set(reality) - {
        "public-key", "short-id", "support-x25519mlkem768"
    }:
        raise ValueError("unsupported Reality options")
    key = reality.get("public-key", "")
    if not isinstance(key, str) or not re.fullmatch(r"[A-Za-z0-9_-]{43}", key):
        raise ValueError("Reality public key must be base64url-encoded X25519")
    if len(base64.urlsafe_b64decode(key + "=")) != 32:
        raise ValueError("Reality public key length is invalid")
    short_id = reality.get("short-id", "")
    if not isinstance(short_id, str) or not re.fullmatch(r"(?:[0-9a-fA-F]{2}){0,8}", short_id):
        raise ValueError("Reality short id must contain up to 8 hex bytes")
    if "support-x25519mlkem768" in reality and type(reality["support-x25519mlkem768"]) is not bool:
        raise ValueError("Reality ML-KEM support flag must be boolean")
    return {
        "mixed-port": mixed_port, "port": 0, "socks-port": 0, "redir-port": 0, "tproxy-port": 0,
        "allow-lan": False, "bind-address": "127.0.0.1", "mode": "rule", "log-level": "info",
        "ipv6": False, "find-process-mode": "off", "interface-name": "", "routing-mark": 0,
        "tun": {"enable": False, "auto-route": False, "auto-detect-interface": False, "dns-hijack": []},
        "dns": {"enable": False}, "sniffer": {"enable": False}, "ntp": {"enable": False},
        "listeners": [], "tunnels": [], "proxy-providers": {}, "rule-providers": {},
        "external-controller": "", "external-controller-tls": "", "external-controller-unix": "",
        "external-controller-pipe": "", "external-ui": "", "external-ui-url": "", "hosts": {},
        "geo-auto-update": False, "profile": {"store-selected": False, "store-fake-ip": False},
        "proxies": [node], "proxy-groups": [{"name": "PROBE", "type": "select", "proxies": [node["name"]]}],
        "rules": ["MATCH,PROBE"],
    }


def read_frame(sock, deadline=None):
    def exact(size):
        data = bytearray()
        while len(data) < size:
            if deadline is not None:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError("core IPC request timed out")
                sock.settimeout(remaining)
            try:
                part = sock.recv(size - len(data))
            except socket.timeout:
                if deadline is not None:
                    raise TimeoutError("core IPC request timed out") from None
                raise
            if not part:
                raise EOFError("IPC connection closed")
            data.extend(part)
        return bytes(data)
    size, = struct.unpack("<I", exact(4))
    if not 0 < size <= MAX_FRAME:
        raise ValueError("IPC frame size is invalid")
    data = json.loads(exact(size))
    if not isinstance(data, dict):
        raise ValueError("IPC response must be an object")
    return data


def write_frame(sock, payload):
    data = json.dumps(payload, separators=(",", ":")).encode()
    if len(data) > MAX_FRAME:
        raise ValueError("IPC frame is too large")
    sock.sendall(struct.pack("<I", len(data)) + data)


def run_lifecycle(session, home, config, hook):
    try:
        session.request("getConfig", str(home / "config.yaml"))
        if session.request("validateConfig", str(home / "config.yaml")) != "":
            raise RuntimeError("core rejected lab config")
        params = {"home-dir": str(home), "version": CORE_VERSION}
        if session.request("initClash", json.dumps(params)) is not True:
            raise RuntimeError("core initClash failed")
        params = {"selected-map": {"PROBE": config["proxies"][0]["name"]}, "test-url": TEST_URL}
        if session.request("setupConfig", json.dumps(params)) != "":
            raise RuntimeError("core setupConfig failed")
        if session.request("startListener") is not True:
            raise RuntimeError("core startListener failed")
        return hook()
    finally:
        for method in ("stopListener", "shutdown"):
            try:
                session.request(method)
            except (OSError, ValueError, RuntimeError, EOFError):
                pass  # Session.close still terminates the owned child if IPC failed.


class IPCSession:
    def __init__(self, sock, record, timeout=5):
        self.sock = sock
        self.record = record
        self.timeout = timeout
        self.sequence = 0

    def request(self, method, data=None):
        self.sequence += 1
        request_id = str(self.sequence)
        deadline = time.monotonic() + self.timeout
        self.sock.settimeout(self.timeout)
        write_frame(self.sock, {"id": request_id, "method": method, "data": data})
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("core IPC request timed out")
            self.sock.settimeout(remaining)
            response = read_frame(self.sock, deadline=deadline)
            if time.monotonic() >= deadline:
                raise TimeoutError("core IPC request timed out")
            if response.get("method") == "message":
                event = response.get("data", {})
                event_type = event.get("type") if isinstance(event, dict) else "unknown"
                if event_type not in {"loaded", "request", "log", "delay", "geoUpdate"}:
                    event_type = "unknown"
                self.record({"event": event_type})
                continue
            if response.get("id") != request_id or response.get("method") != method:
                raise RuntimeError("unexpected core IPC response")
            self.record({"method": method, "ok": response.get("code") == 0})
            if response.get("code") != 0:
                raise RuntimeError("core IPC action failed")
            return response.get("data")


class CoreSession:
    def __init__(self, root, core_command, timeout=5):
        self.root = root
        self.core_command = core_command
        self.timeout = timeout
        self.process = None
        self.listener = None
        self.sock = None
        self.output = None
        self.events = None
        self.ipc = None

    def __enter__(self):
        try:
            self.listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.listener.settimeout(self.timeout)
            self.listener.bind(str(self.root / "core.sock"))
            os.chmod(self.root / "core.sock", 0o600)
            self.listener.listen(1)
            self.output = os.fdopen(os.open(self.root / "core-output.log", os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                                           0o600), "wb")
            self.events = os.fdopen(os.open(self.root / "ipc-events.jsonl", os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                                           0o600), "w")
            environment = {key: value for key, value in os.environ.items()
                           if key.lower() not in {"http_proxy", "https_proxy", "all_proxy", "no_proxy"}}
            self.process = subprocess.Popen(self.core_command + [str(self.root / "core.sock")],
                                            cwd=self.root, stdin=subprocess.DEVNULL, stdout=self.output,
                                            stderr=subprocess.STDOUT, env=environment)
            try:
                self.sock, _ = self.listener.accept()
            except socket.timeout:
                raise TimeoutError("core did not connect to the private socket") from None
            self.listener.close()
            self.listener = None
            self.ipc = IPCSession(self.sock, self.record, self.timeout)
            return self
        except BaseException:
            self.close()
            raise

    def record(self, event):
        self.events.write(json.dumps(event, separators=(",", ":")) + "\n")
        self.events.flush()

    def request(self, method, data=None):
        return self.ipc.request(method, data)

    def close(self):
        for channel in (self.sock, self.listener):
            if channel is not None:
                channel.close()
        if self.process is not None:
            try:
                self.process.wait(timeout=0.5)
            except subprocess.TimeoutExpired:
                self.process.terminate()
                try:
                    self.process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait(timeout=1)
        for output in (self.output, self.events):
            if output is not None:
                output.close()
        socket_path = self.root / "core.sock"
        if socket_path.exists():
            socket_path.unlink()

    def __exit__(self, *unused):
        self.close()
        return False


def validate_url(url):
    if not isinstance(url, str) or len(url) > 2000 or any(ord(char) < 33 for char in url):
        raise ValueError("HTTPS target must be a short URL without whitespace")
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username is not None or parsed.password is not None:
        raise ValueError("only HTTPS targets without credentials are allowed")
    try:
        parsed.port
    except ValueError:
        raise ValueError("HTTPS target has an invalid port") from None
    return url


def run_curl(url, port, timeout, curl="curl"):
    url = validate_url(url)
    parsed = urlsplit(url)
    command = [curl, "-q", "--silent", "--show-error", "--fail", "--location", "--proto", "=https",
               "--proto-redir", "=https", "--noproxy", "", "--proxy", f"http://127.0.0.1:{port}",
               "--connect-timeout", str(min(10, timeout)), "--max-time", str(timeout),
               "--output", os.devnull, "--write-out", "%{http_code}\t%{size_download}\t%{time_total}\n", url]
    environment = {key: value for key, value in os.environ.items()
                   if key.lower() not in {"http_proxy", "https_proxy", "all_proxy", "no_proxy"}}
    result = {"target": f"https://{parsed.netloc}{parsed.path}", "ok": False}
    try:
        process = subprocess.run(command, capture_output=True, text=True, timeout=timeout + 2,
                                 env=environment)
        result["curl_exit"] = process.returncode
        try:
            status, size, elapsed = process.stdout.strip().split("\t")
            result.update(http_status=int(status), bytes_downloaded=int(float(size)), seconds=float(elapsed))
            result["ok"] = process.returncode == 0 and 200 <= int(status) < 400
        except (ValueError, OverflowError):
            result["error"] = "invalid curl transfer metrics"
    except subprocess.TimeoutExpired:
        result.update(curl_exit=124, error="curl subprocess timed out")
    return result


def run_probe(config_path, mixed_port, urls, timeout=30, core_command=None):
    config_path = Path(config_path)
    if config_path.stat().st_size > MAX_FRAME:
        raise ValueError("profile is too large")
    config = sanitize_profile(json.loads(config_path.read_text()), mixed_port)
    if type(timeout) not in (int, float) or not 1 <= timeout <= 60:
        raise ValueError("request timeout must be in 1–60 seconds")
    if len(urls) > 5:
        raise ValueError("at most five HTTPS targets are allowed")
    urls = [validate_url(url) for url in urls]
    # Refuse an occupied port before starting this core; never touch its owner.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as check:
        check.bind(("127.0.0.1", mixed_port))
    root = Path(tempfile.mkdtemp(prefix="fcprobe-", dir="/private/tmp"))
    os.chmod(root, 0o700)
    home = root / "data"
    home.mkdir(mode=0o700)
    with os.fdopen(os.open(home / "config.yaml", os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600), "w") as output:
        json.dump(config, output, indent=2)
    result = {"ok": False, "workdir": str(root), "proxy_port": mixed_port,
              "node_port": config["proxies"][0]["port"], "requests": [],
              "support_x25519mlkem768": config["proxies"][0]["reality-opts"].get("support-x25519mlkem768", False)}
    session = CoreSession(root, core_command or [DEFAULT_CORE], timeout=5)
    try:
        with session:
            def hook():
                deadline = time.monotonic() + 3
                while True:
                    try:
                        with socket.create_connection(("127.0.0.1", mixed_port), timeout=0.3):
                            break
                    except OSError:
                        if time.monotonic() >= deadline:
                            raise TimeoutError("private mixed listener did not become ready") from None
                        time.sleep(0.05)
                return [run_curl(url, mixed_port, timeout) for url in urls]
            result["requests"] = run_lifecycle(session, home, config, hook)
            result["ok"] = all(request["ok"] for request in result["requests"])
            result["mode"] = "https_requests" if urls else "startup_smoke"
    except (OSError, RuntimeError, ValueError, EOFError) as error:
        result["error_type"] = type(error).__name__
        result["error"] = "isolated core startup or lifecycle failed; inspect private core-output.log"
    finally:
        result["core_exit"] = session.process.returncode if session.process is not None else None
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as check:
            check.settimeout(0.3)
            result["listener_closed"] = check.connect_ex(("127.0.0.1", mixed_port)) != 0
        result["ok"] = result["ok"] and result["listener_closed"] and result["core_exit"] == 0
        with os.fdopen(os.open(root / "result.json", os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600), "w") as output:
            json.dump(result, output, indent=2)
    return result


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path, help="explicit JSON node or profile with one lab node")
    parser.add_argument("--port", type=int, default=28791, help="unused loopback proxy port in 20000–31999")
    parser.add_argument("--url", action="append", default=[], help="HTTPS target; repeat for up to five requests")
    parser.add_argument("--timeout", type=float, default=30, help="per-request timeout in seconds (1–60)")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    try:
        result = run_probe(args.config, args.port, args.url, args.timeout)
    except (OSError, ValueError) as error:
        result = {"ok": False, "error_type": type(error).__name__, "error": "invalid profile, target, or occupied lab port"}
    print(json.dumps(result, separators=(",", ":")))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
