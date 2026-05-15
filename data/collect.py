import os
import sys
import json
import time
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

token = os.getenv("GITHUB_TOKEN")
owner = os.getenv("GITHUB_TARGET_OWNER")
repo = os.getenv("GITHUB_TARGET_REPO")

if not all([token, owner, repo]):
    print("Error: GITHUB_TOKEN, GITHUB_TARGET_OWNER, and GITHUB_TARGET_REPO must all be set in .env")
    sys.exit(1)

headers = {
    "Authorization": f"Bearer {token}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}

OUT_DIR = f"data/raw/{owner}_{repo}"
os.makedirs(OUT_DIR, exist_ok=True)


def fetch(path):
    url = f"https://api.github.com/repos/{owner}/{repo}/{path}"
    backoff = 1
    while True:
        try:
            response = requests.get(url, headers=headers)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            print("Network error — retrying in 10 seconds")
            time.sleep(10)
            continue

        if response.status_code == 401:
            print("Auth failed: GITHUB_TOKEN is invalid or expired.")
            sys.exit(1)

        if response.status_code in (403, 429):
            reset_ts = response.headers.get("X-RateLimit-Reset")
            if reset_ts:
                wait = max(0, int(reset_ts) - int(time.time())) + 1
                resume_at = datetime.fromtimestamp(int(reset_ts)).strftime("%-I:%M%p")
            else:
                wait = backoff
                resume_at = f"~{backoff}s"
            minutes = round(wait / 60)
            print(f"Rate limit hit — waiting until {resume_at} ({minutes} minutes)")
            time.sleep(wait)
            backoff = min(backoff * 2, 60)
            continue

        if not response.ok:
            print(f"GitHub API error {response.status_code} for {path}: {response.text}")
            sys.exit(1)

        time.sleep(0.5)
        return response.json(), response.headers


already_saved = {
    int(f[:-5]) for f in os.listdir(OUT_DIR) if f.endswith(".json")
}
print(f"Resuming: {len(already_saved)} PRs already saved, skipping those.")

total_saved = 0
page = 1
last_headers = {}

while True:
    prs, last_headers = fetch(f"pulls?state=closed&per_page=100&page={page}")
    if not prs:
        break

    for pr in prs:
        if pr.get("merged_at") is None:
            continue

        pr_number = pr["number"]
        if pr_number in already_saved:
            continue

        files, last_headers = fetch(f"pulls/{pr_number}/files")
        comments, last_headers = fetch(f"pulls/{pr_number}/comments")
        reviews, last_headers = fetch(f"pulls/{pr_number}/reviews")

        record = {
            "pr_number": pr_number,
            "title": pr["title"],
            "body": pr["body"],
            "merged_at": pr["merged_at"],
            "files": files,
            "comments": comments,
            "reviews": reviews,
        }

        out_path = os.path.join(OUT_DIR, f"{pr_number}.json")
        with open(out_path, "w") as f:
            json.dump(record, f)

        total_saved += 1
        print(f"Saved PR #{pr_number} ({total_saved} total)")

        if total_saved % 50 == 0:
            remaining = last_headers.get("X-RateLimit-Remaining", "?")
            reset_ts = last_headers.get("X-RateLimit-Reset")
            reset_str = datetime.fromtimestamp(int(reset_ts)).strftime("%-I:%M%p") if reset_ts else "?"
            print(f"  Rate limit: {remaining} requests remaining, resets at {reset_str}")

    page += 1

print(f"\nDone. {total_saved} PRs saved to {OUT_DIR}/")
