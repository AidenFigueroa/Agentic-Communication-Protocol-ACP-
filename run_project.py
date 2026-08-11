from __future__ import annotations

import json
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from urllib.parse import urlparse
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


HOST = "127.0.0.1"

OLLAMA_PORT = 11434
INTENT_API_PORT = 8000
STORE_SUPPORT_PORT = 8101
STORE_ORDERS_PORT = 8102
FRONTEND_START_PORT = 5500

OLLAMA_MODEL = "gemma3:1b"

ALLOWED_SPACE_ENDPOINTS = {
    "http://127.0.0.1:8101/tasks",
    "http://127.0.0.1:8102/tasks",
}

PROJECT_DIR = Path(__file__).resolve().parent
FRONTEND_FILE = PROJECT_DIR / "space_frontend.html"

children: list[subprocess.Popen] = []
frontend_server: ThreadingHTTPServer | None = None
frontend_port: int | None = None


def port_is_open(port: int, timeout: float = 0.25) -> bool:
    try:
        with socket.create_connection((HOST, port), timeout=timeout):
            return True
    except OSError:
        return False


def find_free_frontend_port(
    start_port: int = FRONTEND_START_PORT,
    max_tries: int = 50,
) -> int:
    for port in range(
        start_port,
        start_port + max_tries,
    ):
        if not port_is_open(port):
            return port

    raise RuntimeError(
        "Could not find a free frontend port between "
        f"{start_port} and {start_port + max_tries - 1}."
    )


def wait_for_port(
    port: int,
    name: str,
    timeout: float = 30.0,
) -> None:
    deadline = time.time() + timeout

    while time.time() < deadline:
        if port_is_open(port):
            print(f"[OK] {name} is running on port {port}.")
            return

        time.sleep(0.25)

    raise RuntimeError(
        f"{name} did not start on port {port} "
        f"within {timeout:.0f} seconds."
    )


def start_process(
    command: list[str],
    name: str,
) -> subprocess.Popen:
    print(f"[START] {name}")

    process = subprocess.Popen(
        command,
        cwd=str(PROJECT_DIR),
    )

    children.append(process)
    return process


def check_required_files() -> None:
    required = [
        PROJECT_DIR / "intent_api.py",
        PROJECT_DIR / "space_registry.py",
        PROJECT_DIR / "store_support_space.py",
        PROJECT_DIR / "store_orders_space.py",
        FRONTEND_FILE,
    ]

    missing = [
        path.name
        for path in required
        if not path.exists()
    ]

    if missing:
        print("\nMissing required files:")

        for name in missing:
            print(f"  - {name}")

        raise SystemExit(
            "\nPut the launcher files and space_frontend.html "
            "directly inside your ACPS project folder."
        )


def ensure_ollama() -> None:
    if port_is_open(OLLAMA_PORT):
        print("[OK] Ollama is already running.")

    else:
        ollama = shutil.which("ollama")

        if ollama is None:
            raise RuntimeError(
                "Ollama was not found. Make sure Ollama is "
                "installed and the 'ollama' command works."
            )

        start_process(
            [ollama, "serve"],
            "Ollama",
        )

        wait_for_port(
            OLLAMA_PORT,
            "Ollama",
            timeout=20,
        )

    try:
        with urllib.request.urlopen(
            f"http://{HOST}:{OLLAMA_PORT}/api/tags",
            timeout=5,
        ) as response:
            tags = response.read().decode("utf-8")

    except urllib.error.URLError as error:
        raise RuntimeError(
            f"Could not communicate with Ollama: {error}"
        ) from error

    if OLLAMA_MODEL not in tags:
        ollama = shutil.which("ollama")

        if ollama is None:
            raise RuntimeError(
                "The Ollama service is running, but the "
                "'ollama' command could not be found."
            )

        print(
            f"[MODEL] Downloading missing model "
            f"{OLLAMA_MODEL}..."
        )

        result = subprocess.run(
            [ollama, "pull", OLLAMA_MODEL],
            cwd=str(PROJECT_DIR),
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"Could not download {OLLAMA_MODEL}."
            )

    else:
        print(
            f"[OK] Ollama model {OLLAMA_MODEL} "
            "is available."
        )


def start_if_needed(
    port: int,
    command: list[str],
    name: str,
) -> None:
    if port_is_open(port):
        print(
            f"[OK] {name} is already running "
            f"on port {port}."
        )
        return

    start_process(command, name)
    wait_for_port(port, name)


class FrontendHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            directory=str(PROJECT_DIR),
            **kwargs,
        )

    def log_message(self, format: str, *args) -> None:
        # Keep the launcher output readable.
        return

    def _proxy(
        self,
        method: str,
        destination: str,
    ) -> None:
        body: bytes | None = None

        if method == "POST":
            content_length = int(
                self.headers.get(
                    "Content-Length",
                    "0",
                )
            )
            body = self.rfile.read(content_length)

        request = urllib.request.Request(
            url=destination,
            data=body,
            method=method,
            headers={
                "Content-Type": self.headers.get(
                    "Content-Type",
                    "application/json",
                ),
            },
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=120,
            ) as response:
                response_body = response.read()

                self.send_response(response.status)
                self.send_header(
                    "Content-Type",
                    response.headers.get(
                        "Content-Type",
                        "application/json",
                    ),
                )
                self.send_header(
                    "Content-Length",
                    str(len(response_body)),
                )
                self.end_headers()
                self.wfile.write(response_body)

        except urllib.error.HTTPError as error:
            response_body = error.read()

            self.send_response(error.code)
            self.send_header(
                "Content-Type",
                error.headers.get(
                    "Content-Type",
                    "application/json",
                ),
            )
            self.send_header(
                "Content-Length",
                str(len(response_body)),
            )
            self.end_headers()
            self.wfile.write(response_body)

        except Exception as error:
            response_body = json.dumps(
                {
                    "error": "proxy_error",
                    "details": str(error),
                }
            ).encode("utf-8")

            self.send_response(502)
            self.send_header(
                "Content-Type",
                "application/json",
            )
            self.send_header(
                "Content-Length",
                str(len(response_body)),
            )
            self.end_headers()
            self.wfile.write(response_body)

    def do_GET(self) -> None:
        if self.path == "/health/router":
            self._proxy(
                "GET",
                f"http://{HOST}:{INTENT_API_PORT}/",
            )
            return

        if self.path == "/health/support":
            self._proxy(
                "GET",
                f"http://{HOST}:{STORE_SUPPORT_PORT}/",
            )
            return

        if self.path == "/health/orders":
            self._proxy(
                "GET",
                f"http://{HOST}:{STORE_ORDERS_PORT}/",
            )
            return

        if self.path in {"/", ""}:
            self.send_response(302)
            self.send_header(
                "Location",
                "/space_frontend.html",
            )
            self.end_headers()
            return

        super().do_GET()

    def _send_json_response(
        self,
        status_code: int,
        payload: dict,
    ) -> None:
        response_body = json.dumps(
            payload
        ).encode("utf-8")

        self.send_response(status_code)
        self.send_header(
            "Content-Type",
            "application/json",
        )
        self.send_header(
            "Content-Length",
            str(len(response_body)),
        )
        self.end_headers()
        self.wfile.write(response_body)

    def _send_space_request(self) -> None:
        try:
            content_length = int(
                self.headers.get(
                    "Content-Length",
                    "0",
                )
            )

            request_body = self.rfile.read(
                content_length
            )

            wrapper = json.loads(
                request_body.decode("utf-8")
            )

            endpoint = wrapper.get("endpoint")
            protocol_message = wrapper.get(
                "protocol_message"
            )

            if endpoint not in ALLOWED_SPACE_ENDPOINTS:
                self._send_json_response(
                    400,
                    {
                        "error": "invalid_space_endpoint",
                        "details": endpoint,
                    },
                )
                return

            if not isinstance(
                protocol_message,
                dict,
            ):
                self._send_json_response(
                    400,
                    {
                        "error": "invalid_protocol_message",
                    },
                )
                return

            body = json.dumps(
                protocol_message
            ).encode("utf-8")

            request = urllib.request.Request(
                url=endpoint,
                data=body,
                method="POST",
                headers={
                    "Content-Type": "application/json",
                },
            )

            try:
                with urllib.request.urlopen(
                    request,
                    timeout=30,
                ) as response:
                    response_body = response.read()
                    status_code = response.status
                    content_type = (
                        response.headers.get(
                            "Content-Type",
                            "application/json",
                        )
                    )

            except urllib.error.HTTPError as error:
                response_body = error.read()
                status_code = error.code
                content_type = (
                    error.headers.get(
                        "Content-Type",
                        "application/json",
                    )
                )

            self.send_response(status_code)
            self.send_header(
                "Content-Type",
                content_type,
            )
            self.send_header(
                "Content-Length",
                str(len(response_body)),
            )
            self.end_headers()
            self.wfile.write(response_body)

        except (
            json.JSONDecodeError,
            TypeError,
            ValueError,
            urllib.error.URLError,
        ) as error:
            self._send_json_response(
                502,
                {
                    "error": "space_proxy_error",
                    "details": str(error),
                },
            )

    def do_POST(self) -> None:
        if self.path == "/api/route-intent":
            self._proxy(
                "POST",
                (
                    f"http://{HOST}:{INTENT_API_PORT}"
                    "/route-intent"
                ),
            )
            return

        if self.path == "/api/send-space":
            self._send_space_request()
            return

        self._send_json_response(
            404,
            {
                "error": "endpoint_not_found",
            },
        )


def start_frontend_server() -> int:
    global frontend_server
    global frontend_port

    frontend_port = find_free_frontend_port()

    if frontend_port != FRONTEND_START_PORT:
        print(
            f"[INFO] Port {FRONTEND_START_PORT} is busy. "
            f"Using port {frontend_port} instead."
        )

    frontend_server = ThreadingHTTPServer(
        (HOST, frontend_port),
        FrontendHandler,
    )

    thread = threading.Thread(
        target=frontend_server.serve_forever,
        daemon=True,
    )
    thread.start()

    wait_for_port(
        frontend_port,
        "Frontend",
        timeout=10,
    )

    return frontend_port


def stop_everything() -> None:
    global frontend_server

    if frontend_server is not None:
        frontend_server.shutdown()
        frontend_server.server_close()
        frontend_server = None

    if children:
        print("\nStopping services...")

    for process in reversed(children):
        if process.poll() is None:
            process.terminate()

    for process in reversed(children):
        if process.poll() is None:
            try:
                process.wait(timeout=4)
            except subprocess.TimeoutExpired:
                process.kill()

    print("Stopped.")


def main() -> None:
    check_required_files()

    try:
        ensure_ollama()

        start_if_needed(
            INTENT_API_PORT,
            [
                sys.executable,
                "-m",
                "uvicorn",
                "intent_api:app",
                "--host",
                HOST,
                "--port",
                str(INTENT_API_PORT),
            ],
            "Intent API",
        )

        start_if_needed(
            STORE_SUPPORT_PORT,
            [
                sys.executable,
                str(
                    PROJECT_DIR
                    / "store_support_space.py"
                ),
            ],
            "Store Support Space",
        )

        start_if_needed(
            STORE_ORDERS_PORT,
            [
                sys.executable,
                str(
                    PROJECT_DIR
                    / "store_orders_space.py"
                ),
            ],
            "Store Orders Space",
        )

        print("[START] Frontend")
        selected_frontend_port = (
            start_frontend_server()
        )

        url = (
            f"http://{HOST}:"
            f"{selected_frontend_port}"
            "/space_frontend.html"
        )

        print("\n" + "=" * 58)
        print("ACPS IS RUNNING")
        print("=" * 58)
        print(f"Frontend:      {url}")
        print(
            f"Intent API:    "
            f"http://{HOST}:{INTENT_API_PORT}"
        )
        print(
            f"Store Support: "
            f"http://{HOST}:{STORE_SUPPORT_PORT}"
        )
        print(
            f"Store Orders:  "
            f"http://{HOST}:{STORE_ORDERS_PORT}"
        )
        print()
        print(
            "Press Ctrl+C in this window "
            "to stop the launcher."
        )
        print("=" * 58 + "\n")

        webbrowser.open(url)

        while True:
            for process in children:
                return_code = process.poll()

                if return_code is not None:
                    raise RuntimeError(
                        "A service stopped unexpectedly "
                        f"with code {return_code}."
                    )

            time.sleep(1)

    except KeyboardInterrupt:
        pass

    except Exception as error:
        print(f"\nERROR: {error}")
        input(
            "\nPress Enter to close..."
        )

    finally:
        stop_everything()


if __name__ == "__main__":
    main()
