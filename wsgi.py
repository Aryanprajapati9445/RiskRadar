"""
WSGI Entrypoint for Gunicorn and Flask Server
"""

import os
import socket
from app import create_app

# Load .env file manually if present (no extra external dependency needed)
env_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(env_path):
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())
    except Exception:
        pass

app = create_app()


def is_port_available(port: int) -> bool:
    """Check if a port can be safely bound on 0.0.0.0."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("0.0.0.0", port))
            return True
        except OSError:
            return False


if __name__ == "__main__":
    env_port = os.environ.get("PORT")
    requested_port = int(env_port) if env_port else 5000
    port = requested_port

    if not is_port_available(port):
        # Automatically find the first free port (5001, 5002, etc.)
        for candidate in range(5001, 5020):
            if is_port_available(candidate):
                print("\n" + "=" * 65)
                print(f"  ⚠️  Notice: Port {port} is currently occupied.")
                print(f"  🔄 Automatically running on: http://localhost:{candidate}")
                print("=" * 65 + "\n")
                port = candidate
                break

    app.run(host="0.0.0.0", port=port, debug=False)
