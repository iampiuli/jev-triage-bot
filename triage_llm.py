"""Triage issues with gpt-4o-mini in JSON mode."""
import json
import os
import sys
import time

from dotenv import load_dotenv
from openai import OpenAI, OpenAIError

from common import CATEGORIES, issue_state, load_issues, save

load_dotenv()

# Any OpenAI-compatible provider works; defaults to OpenAI's gpt-4o-mini.
MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
BASE_URL = os.getenv("LLM_BASE_URL")  # e.g. Gemini's OpenAI-compatible endpoint
API_KEY = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")

SYSTEM = f"""You triage GitHub issues. Answer four questions and reply with a JSON object with exactly these keys:
- "category": one of {CATEGORIES}
- "priority": integer 1-5 (1 = trivial/cosmetic, 5 = critical: crash, data loss, security, widespread breakage)
- "needs_more_info": true if the issue lacks information (repro steps, versions, expected behavior) maintainers need to act on it, else false
- "duplicate_likely": true if this is likely a duplicate of a commonly reported existing issue, else false"""


def validate(d):
    if d.get("category") not in CATEGORIES:
        raise ValueError(f"bad category: {d.get('category')!r}")
    p = d.get("priority")
    if isinstance(p, bool) or not isinstance(p, int) or not 1 <= p <= 5:
        raise ValueError(f"bad priority: {p!r}")
    for k in ("needs_more_info", "duplicate_likely"):
        if not isinstance(d.get(k), bool):
            raise ValueError(f"bad {k}: {d.get(k)!r}")


def main():
    if not API_KEY:
        sys.exit("LLM_API_KEY (or OPENAI_API_KEY) is not set")
    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
    print(f"Model: {MODEL}  Endpoint: {BASE_URL or 'api.openai.com'}")
    results = []
    for issue in load_issues():
        start = time.perf_counter()
        try:
            resp = client.chat.completions.create(
                model=MODEL,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": SYSTEM},
                    {"role": "user", "content": issue_state(issue)},
                ],
            )
        except OpenAIError as e:
            sys.exit(f"OpenAI call failed on #{issue['number']}: {e}")
        latency = time.perf_counter() - start

        raw = resp.choices[0].message.content
        row = {
            "number": issue["number"],
            "title": issue["title"],
            "latency_s": latency,
            "model": MODEL,
            "input_tokens": resp.usage.prompt_tokens,
            "output_tokens": resp.usage.completion_tokens,
            "raw": raw,
            "parse_error": None,
        }
        try:
            parsed = json.loads(raw)
            validate(parsed)
            row.update({k: parsed[k] for k in
                        ("category", "priority", "needs_more_info", "duplicate_likely")})
        except (json.JSONDecodeError, ValueError, TypeError, AttributeError) as e:
            row["parse_error"] = f"{type(e).__name__}: {e}"
            print(f"  PARSE FAILURE on #{issue['number']}: {row['parse_error']}")
        results.append(row)
        print(f"#{issue['number']}: {row.get('category')} p{row.get('priority')} "
              f"info={row.get('needs_more_info')} dup={row.get('duplicate_likely')} "
              f"({latency:.2f}s, {row['input_tokens']}+{row['output_tokens']} tokens)")

    save("llm_results.json", results)
    print("Saved results/llm_results.json")


if __name__ == "__main__":
    main()
