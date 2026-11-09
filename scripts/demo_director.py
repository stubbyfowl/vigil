"""Start Vigil and play the demo, or control a server that is already running.

  python scripts/demo_director.py serve     start the server, open the browser, play the demo
  python scripts/demo_director.py start     play on a running server
  python scripts/demo_director.py next      skip to the next beat
  python scripts/demo_director.py stop      stop the demo
  python scripts/demo_director.py status    print the current beat
"""

import argparse
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STARTUP_SECONDS = 30


def call(port: int, path: str, method: str = "GET") -> dict:
    data = b"{}" if method == "POST" else None
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}", data=data, method=method, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        return json.load(response)


def wait_for_server(port: int) -> None:
    deadline = time.time() + STARTUP_SECONDS
    while time.time() < deadline:
        try:
            call(port, "/api/health")
            return
        except (urllib.error.URLError, ConnectionError):
            time.sleep(0.3)
    sys.exit(f"The server did not start within {STARTUP_SECONDS} seconds.")


def serve(port: int) -> None:
    server = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(port)], cwd=ROOT / "backend"
    )
    try:
        wait_for_server(port)
        url = f"http://localhost:{port}/#/?autoplay=1"
        print(f"\nVigil is running at {url}\nGround screen for a second window: http://localhost:{port}/#/ground?pin=1\nPress Ctrl+C to stop.\n")
        webbrowser.open(url)
        server.wait()
    except KeyboardInterrupt:
        pass
    finally:
        server.terminate()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["serve", "start", "next", "stop", "status"])
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    if args.command == "serve":
        serve(args.port)
    elif args.command == "status":
        print(json.dumps(call(args.port, "/api/live")["demo"], indent=2))
    else:
        print(json.dumps(call(args.port, f"/api/demo/{args.command}", "POST")["demo"], indent=2))


if __name__ == "__main__":
    main()
