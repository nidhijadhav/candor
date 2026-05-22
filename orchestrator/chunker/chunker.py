from dataclasses import dataclass, field


@dataclass
class DiffChunk:
    file: str
    hunk_header: str
    changed_lines: list[str]
    context_lines: list[str]


def parse_diff(
    diff: str,
    context_lines: int = 5,
    max_hunk_lines: int = 150,
) -> list[DiffChunk]:
    if not diff or not diff.strip():
        return []

    try:
        return _parse(diff, context_lines, max_hunk_lines)
    except Exception:
        return []


def _parse(diff: str, context_lines: int, max_hunk_lines: int) -> list[DiffChunk]:
    chunks: list[DiffChunk] = []
    current_file: str = ""
    hunk_header: str = ""
    hunk_lines: list[str] = []

    def flush(file: str, header: str, lines: list[str]) -> None:
        if not file or not lines:
            return
        for chunk in _split_hunk(file, header, lines, context_lines, max_hunk_lines):
            chunks.append(chunk)

    for line in diff.splitlines():
        # New file header
        if line.startswith("+++ "):
            flush(current_file, hunk_header, hunk_lines)
            hunk_header = ""
            hunk_lines = []
            path = line[4:]
            # Strip b/ prefix used in git diffs; keep as-is for /dev/null
            if path.startswith("b/"):
                path = path[2:]
            current_file = path
            continue

        # Skip the --- line — we only care about the +++ (new) path
        if line.startswith("--- "):
            continue

        # Binary file marker
        if "Binary files" in line:
            flush(current_file, hunk_header, hunk_lines)
            hunk_header = ""
            hunk_lines = []
            current_file = ""
            continue

        # Hunk header
        if line.startswith("@@"):
            flush(current_file, hunk_header, hunk_lines)
            hunk_header = line
            hunk_lines = []
            continue

        # diff --git header resets file tracking until +++ is seen
        if line.startswith("diff --git"):
            flush(current_file, hunk_header, hunk_lines)
            hunk_header = ""
            hunk_lines = []
            current_file = ""
            continue

        if current_file and hunk_header:
            hunk_lines.append(line)

    flush(current_file, hunk_header, hunk_lines)
    return chunks


def _split_hunk(
    file: str,
    header: str,
    lines: list[str],
    context_lines: int,
    max_hunk_lines: int,
) -> list[DiffChunk]:
    chunks: list[DiffChunk] = []

    for start in range(0, max(1, len(lines)), max_hunk_lines):
        segment = lines[start:start + max_hunk_lines]

        changed = [l for l in segment if l.startswith(("+", "-"))]
        # Unchanged lines within this segment are its natural context
        context = [l for l in segment if not l.startswith(("+", "-"))]
        # For split hunks also include the tail of the previous segment as overlap
        if start > 0:
            tail = lines[max(0, start - context_lines):start]
            context = [l for l in tail if not l.startswith(("+", "-"))] + context

        chunks.append(DiffChunk(
            file=file,
            hunk_header=header,
            changed_lines=changed,
            context_lines=context,
        ))

    return chunks
