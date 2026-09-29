"""Shared constants for the triage demo."""
import json
from pathlib import Path

RESULTS_DIR = Path(__file__).parent / "results"
CATEGORIES = ["bug", "feature", "question", "docs"]
MAX_BODY_CHARS = 4000  # keep both models on identical, bounded input


def load_issues():
    path = RESULTS_DIR / "issues.json"
    if not path.exists():
        raise SystemExit("results/issues.json not found - run fetch_issues.py first")
    return json.loads(path.read_text(encoding="utf-8"))


def issue_state(issue):
    """Identical issue text handed to both models."""
    body = (issue.get("body") or "")[:MAX_BODY_CHARS]
    return f"Title: {issue['title']}\n\nBody:\n{body}"


def save(name, data):
    RESULTS_DIR.mkdir(exist_ok=True)
    (RESULTS_DIR / name).write_text(json.dumps(data, indent=2), encoding="utf-8")
