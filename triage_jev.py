"""Triage issues with TypeSafe's Jev model (System One)."""
import sys
import time

from dotenv import load_dotenv
from typesafe_sdk import Choice, Noul, Score, TypeSafeClient, TypeSafeError

from common import CATEGORIES, issue_state, load_issues, save

load_dotenv()

QUESTIONS = {
    "category": Choice(
        instructions="What kind of GitHub issue is this?",
        criteria={
            "bug": "Something is broken or behaves incorrectly",
            "feature": "A request for new functionality or an enhancement",
            "question": "The author is asking for help or how to do something",
            "docs": "About documentation being missing, wrong, or unclear",
        },
    ),
    # Score levels are zero-indexed; we add 1 to get a 1-5 priority.
    "priority": Score(
        instructions="How urgent is this issue for the maintainers?",
        criteria=[
            "Priority 1: trivial, cosmetic, or nice-to-have",
            "Priority 2: minor, low impact",
            "Priority 3: moderate impact or affects some users",
            "Priority 4: significant, affects many users or blocks workflows",
            "Priority 5: critical - crash, data loss, security, or widespread breakage",
        ],
    ),
    "needs_more_info": Noul(
        instructions="Does the issue lack information (e.g. reproduction steps, "
        "versions, expected behavior) that maintainers need to act on it?"
    ),
    "duplicate_likely": Noul(
        instructions="Is this issue likely a duplicate of a commonly reported "
        "existing issue?"
    ),
}


def main():
    issues = load_issues()
    try:
        client = TypeSafeClient()  # reads TYPESAFE_API_KEY
    except TypeSafeError as e:
        sys.exit(f"Could not create TypeSafe client: {e}")

    results = []
    for issue in issues:
        start = time.perf_counter()
        try:
            resp = client.system_one(issue_state(issue), QUESTIONS)
        except TypeSafeError as e:
            sys.exit(f"Jev call failed on #{issue['number']}: {e}")
        latency = time.perf_counter() - start

        a = resp.answers
        row = {
            "number": issue["number"],
            "title": issue["title"],
            "latency_s": latency,
            "model": resp.model,
            "input_tokens": resp.usage.input_tokens,
            "output_tokens": resp.usage.output_tokens,
            "category": a["category"].choice,
            "category_confidence": a["category"].confidence,
            "priority_raw": a["priority"].score,
            "priority": round(a["priority"].score) + 1,
            "priority_confidence": a["priority"].confidence,
            "needs_more_info_prob": a["needs_more_info"].noul,
            "needs_more_info": a["needs_more_info"].noul >= 0.5,
            "duplicate_likely_prob": a["duplicate_likely"].noul,
            "duplicate_likely": a["duplicate_likely"].noul >= 0.5,
        }
        if row["input_tokens"] is None:
            sys.exit(f"Jev did not report input_tokens for #{issue['number']}; "
                     "cannot compute cost without estimating")
        assert row["category"] in CATEGORIES
        results.append(row)
        print(f"#{issue['number']}: {row['category']} p{row['priority']} "
              f"info={row['needs_more_info']} dup={row['duplicate_likely']} "
              f"({latency:.2f}s, {row['input_tokens']} in-tokens)")

    save("jev_results.json", results)
    print("Saved results/jev_results.json")


if __name__ == "__main__":
    main()
