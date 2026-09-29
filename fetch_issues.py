"""Fetch open issues (no PRs) from a public GitHub repo via the REST API."""
import argparse

import requests

from common import save


def fetch(repo, count):
    issues, page = [], 1
    while len(issues) < count:
        resp = requests.get(
            f"https://api.github.com/repos/{repo}/issues",
            params={"state": "open", "per_page": 50, "page": page},
            headers={"Accept": "application/vnd.github+json"},
            timeout=30,
        )
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        for item in batch:
            if "pull_request" in item:  # the issues endpoint also returns PRs
                continue
            issues.append({
                "number": item["number"],
                "url": item["html_url"],
                "title": item["title"],
                "body": item.get("body") or "",
            })
        page += 1
    return issues[:count]


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("repo", nargs="?", default="facebook/react", help="owner/name")
    ap.add_argument("-n", "--count", type=int, default=15)
    args = ap.parse_args()
    issues = fetch(args.repo, args.count)
    save("issues.json", issues)
    print(f"Saved {len(issues)} issues from {args.repo} to results/issues.json")
    for i in issues:
        print(f"  #{i['number']}: {i['title'][:80]}")
