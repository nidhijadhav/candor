import os
import sys
import json
import requests
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

PR_NUMBER = 29477

def fetch(path):
    url = f"https://api.github.com/repos/{owner}/{repo}/{path}"
    response = requests.get(url, headers=headers)
    if response.status_code == 401:
        print("Auth failed: GITHUB_TOKEN is invalid or expired.")
        sys.exit(1)
    if not response.ok:
        print(f"GitHub API error {response.status_code} for {path}: {response.text}")
        sys.exit(1)
    return response.json()

print(f"=== Files (diff) for PR #{PR_NUMBER} ===")
files = fetch(f"pulls/{PR_NUMBER}/files")
print(json.dumps(files, indent=2))

print(f"\n=== Inline review comments for PR #{PR_NUMBER} ===")
comments = fetch(f"pulls/{PR_NUMBER}/comments")
print(json.dumps(comments, indent=2))

print(f"\n=== Review verdicts for PR #{PR_NUMBER} ===")
reviews = fetch(f"pulls/{PR_NUMBER}/reviews")
for review in reviews:
    print(f"  login={review['user']['login']} association={review['author_association']} state={review['state']}")
print(json.dumps(reviews, indent=2))
