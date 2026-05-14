import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()

token = os.getenv("GITHUB_TOKEN")
owner = os.getenv("GITHUB_TARGET_OWNER")
repo = os.getenv("GITHUB_TARGET_REPO")

if not all([token, owner, repo]):
    print("Error: GITHUB_TOKEN, GITHUB_TARGET_OWNER, and GITHUB_TARGET_REPO must all be set in .env")
    sys.exit(1)

url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
headers = {
    "Authorization": f"Bearer {token}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}

total_merged = 0
page = 1

while True:
    params = {"state": "closed", "per_page": 100, "page": page}
    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 401:
        print("Auth failed: GITHUB_TOKEN is invalid or expired.")
        sys.exit(1)

    if response.status_code == 404:
        print(f"Repo not found: {owner}/{repo}. Check GITHUB_TARGET_OWNER and GITHUB_TARGET_REPO.")
        sys.exit(1)

    if not response.ok:
        print(f"GitHub API error {response.status_code}: {response.text}")
        sys.exit(1)

    prs = response.json()
    if not prs:
        break

    merged = [pr for pr in prs if pr.get("merged_at") is not None]
    total_merged += len(merged)
    print(f"Page {page}: {len(merged)} merged PRs")

    page += 1

print(f"\nTotal merged PRs: {total_merged}")
