"""Low-cost static checks: parse code and protect the chosen dependency direction."""
import ast
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    checked = 0
    for folder in ("server", "scripts", "tests"):
        for file in (ROOT / folder).glob("*.py"):
            ast.parse(file.read_text(), filename=str(file))
            checked += 1
    for folder in ("web", "mini", "build"):
        for file in (ROOT / folder).rglob("*.js"):
            subprocess.run(["node", "--check", str(file)], check=True, capture_output=True)
            checked += 1
    for file in (ROOT / "mini").rglob("*.json"):
        json.loads(file.read_text())
    for name in ("routes.py", "dependencies.py", "app.py"):
        text = (ROOT / "server" / name).read_text()
        if name != "app.py" and ".execute(" in text:
            raise RuntimeError(f"SQL belongs in services, not {name}")
    for template in (ROOT / "mini" / "pages").rglob("*.wxml"):
        import re
        javascript = template.with_suffix(".js").read_text()
        for handler in re.findall(r'bind(?:tap|submit|change)="([A-Za-z_]+)"', template.read_text()):
            if not re.search(r"\b" + handler + r"\s*\(", javascript):
                raise RuntimeError(f"Missing native event handler {handler} in {template}")
    transport = (ROOT / "server" / "mcp.py").read_text()
    if "sqlite3" in transport or "from .db" in transport:
        raise RuntimeError("MCP must use the authenticated HTTP API")
    db = (ROOT / "server" / "db.py").read_text()
    if any(word in db for word in ("memberships", "registrations", "owner_id")):
        raise RuntimeError("Connection layer contains product logic")
    print(f"PASS: {checked} Python/JavaScript files parsed; module boundary checks passed.")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as error:
        sys.stderr.write(error.stderr.decode() if isinstance(error.stderr, bytes) else str(error.stderr))
        raise SystemExit(error.returncode)
