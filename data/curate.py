import os
import json
import fnmatch
import yaml
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize
from dotenv import load_dotenv

load_dotenv()

RAW_DIR = "data/raw/trinodb_trino"
OUT_PATH = "data/curated/trinodb_trino.jsonl"
CONFIG_PATH = "data/curation_config.yaml"

with open(CONFIG_PATH) as f:
    config = yaml.safe_load(f)
generated_patterns = config.get("generated_file_patterns", [])
dedup_threshold = config.get("dedup_similarity_threshold", 0.9)


def is_generated(path):
    if not path:
        return False
    return any(fnmatch.fnmatch(path, p) or p in path for p in generated_patterns)

os.makedirs("data/curated", exist_ok=True)

files = sorted(f for f in os.listdir(RAW_DIR) if f.endswith(".json"))
print(f"Found {len(files)} files in {RAW_DIR}")

comments = []
skipped = 0

for i, filename in enumerate(files, 1):
    try:
        with open(os.path.join(RAW_DIR, filename)) as f:
            pr = json.load(f)
    except (json.JSONDecodeError, OSError):
        skipped += 1
        continue

    for c in pr.get("comments", []):
        comments.append({
            "pr_number": pr["pr_number"],
            "merged_at": pr["merged_at"],
            "file": c.get("path"),
            "diff_hunk": c.get("diff_hunk"),
            "comment_body": c.get("body"),
            "reviewer_association": c.get("author_association"),
        })

    if i % 1000 == 0:
        print(f"  Processed {i}/{len(files)} files ({len(comments)} comments so far)...")

if skipped:
    print(f"Skipped {skipped} unreadable files.")

total = len(comments)
print(f"\nTotal comments before filtering: {total}")

# Filter 1: drop comments under 20 words
before = len(comments)
comments = [c for c in comments if len((c["comment_body"] or "").split()) >= 20]
dropped_short = before - len(comments)
print(f"Dropped (under 20 words):         {dropped_short}")

# Filter 2: drop comments where reviewer association is NONE
before = len(comments)
comments = [c for c in comments if c["reviewer_association"] != "NONE"]
dropped_none = before - len(comments)
print(f"Dropped (association = NONE):      {dropped_none}")

# Filter 3: drop comments from PRs where merged_at is null
before = len(comments)
comments = [c for c in comments if c["merged_at"] is not None]
dropped_unmerged = before - len(comments)
print(f"Dropped (PR not merged):           {dropped_unmerged}")

# Filter 4: drop comments on auto-generated files
before = len(comments)
comments = [c for c in comments if not is_generated(c["file"])]
dropped_generated = before - len(comments)
print(f"Dropped (generated files):         {dropped_generated}")

# Filter 5: deduplicate near-identical comments using TF-IDF cosine similarity
print(f"Deduplicating at threshold {dedup_threshold}...")
bodies = [c["comment_body"] or "" for c in comments]
tfidf = normalize(TfidfVectorizer().fit_transform(bodies))
n = tfidf.shape[0]

# Union-Find
parent = list(range(n))

def find(x):
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x

def union(x, y):
    px, py = find(x), find(y)
    if px != py:
        parent[px] = py

# Chunked pairwise similarity — only upper triangle to avoid double-counting
CHUNK = 500
for start in range(0, n, CHUNK):
    end = min(start + CHUNK, n)
    chunk = tfidf[start:end]
    if end < n:
        sims = (chunk @ tfidf[end:].T).toarray()
        rows, cols = np.where(sims >= dedup_threshold)
        for r, c in zip(rows, cols):
            union(start + r, end + c)
    # Within-chunk upper triangle
    chunk_sims = (chunk @ chunk.T).toarray()
    size = end - start
    rows, cols = np.where(
        (chunk_sims >= dedup_threshold) &
        (np.arange(size)[:, None] < np.arange(size)[None, :])
    )
    for r, c in zip(rows, cols):
        union(start + r, start + c)

seen = set()
kept_indices = []
for i in range(n):
    root = find(i)
    if root not in seen:
        seen.add(root)
        kept_indices.append(i)

before = len(comments)
comments = [comments[i] for i in kept_indices]
dropped_dupes = before - len(comments)
print(f"Dropped (near-duplicates):         {dropped_dupes}")

print(f"Final comment count:               {len(comments)}")

with open(OUT_PATH, "w") as f:
    for c in comments:
        f.write(json.dumps(c) + "\n")

print(f"\nSaved to {OUT_PATH}")
