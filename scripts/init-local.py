"""Create local-only configuration without printing credentials or replacing files."""
from pathlib import Path
import secrets

root = Path(__file__).resolve().parents[1]
target = root / "backend" / ".env"
template = root / "backend" / ".env.example"
if target.exists():
    print("backend/.env already exists; kept unchanged.")
else:
    content = template.read_text(encoding="utf-8")
    content = content.replace("WORKBENCH_SECRET_KEY=\n", "WORKBENCH_SECRET_KEY=" + secrets.token_urlsafe(48) + "\n")
    with target.open("x", encoding="utf-8") as output:
        output.write(content)
    target.chmod(0o600)
    print("Created ignored local configuration. Identity provider remains disabled.")
