import pytest
from orchestrator.chunker.chunker import DiffChunk, parse_diff

SINGLE_FILE_DIFF = """\
diff --git a/Foo.java b/Foo.java
--- a/Foo.java
+++ b/Foo.java
@@ -1,4 +1,5 @@
 class Foo {
-    int x = 0;
+    int x = 1;
+    int y = 2;
 }
"""

MULTI_FILE_DIFF = """\
diff --git a/Foo.java b/Foo.java
--- a/Foo.java
+++ b/Foo.java
@@ -1,3 +1,3 @@
-int x = 0;
+int x = 1;
diff --git a/Bar.java b/Bar.java
--- a/Bar.java
+++ b/Bar.java
@@ -5,3 +5,3 @@
-String s = null;
+String s = "";
"""

BINARY_DIFF = """\
diff --git a/image.png b/image.png
Binary files a/image.png and b/image.png differ
"""

RENAME_DIFF = """\
diff --git a/OldName.java b/NewName.java
--- a/OldName.java
+++ b/NewName.java
@@ -1,3 +1,3 @@
-int x = 0;
+int x = 1;
"""


def test_single_file_diff():
    chunks = parse_diff(SINGLE_FILE_DIFF)
    assert len(chunks) == 1
    assert chunks[0].file == "Foo.java"
    assert chunks[0].hunk_header.startswith("@@")
    assert any("+    int x = 1;" in l for l in chunks[0].changed_lines)
    assert any("-    int x = 0;" in l for l in chunks[0].changed_lines)


def test_multi_file_diff():
    chunks = parse_diff(MULTI_FILE_DIFF)
    assert len(chunks) == 2
    files = {c.file for c in chunks}
    assert files == {"Foo.java", "Bar.java"}


def test_empty_string_returns_empty():
    assert parse_diff("") == []


def test_whitespace_only_returns_empty():
    assert parse_diff("   \n\n  ") == []


def test_binary_file_skipped():
    chunks = parse_diff(BINARY_DIFF)
    assert chunks == []


def test_binary_file_in_multi_file_diff():
    diff = BINARY_DIFF + SINGLE_FILE_DIFF
    chunks = parse_diff(diff)
    assert len(chunks) == 1
    assert chunks[0].file == "Foo.java"


def test_rename_uses_new_path():
    chunks = parse_diff(RENAME_DIFF)
    assert len(chunks) == 1
    assert chunks[0].file == "NewName.java"


def test_oversized_hunk_is_split():
    changed = "\n".join(f"+line {i}" for i in range(300))
    diff = f"diff --git a/Big.java b/Big.java\n--- a/Big.java\n+++ b/Big.java\n@@ -1,300 +1,300 @@\n{changed}\n"
    chunks = parse_diff(diff, max_hunk_lines=150)
    assert len(chunks) == 2
    assert all(c.file == "Big.java" for c in chunks)
    total_changed = sum(len(c.changed_lines) for c in chunks)
    assert total_changed == 300


def test_context_lines_populated():
    diff = """\
diff --git a/Foo.java b/Foo.java
--- a/Foo.java
+++ b/Foo.java
@@ -1,6 +1,6 @@
 context_before_1
 context_before_2
-old line
+new line
 context_after_1
 context_after_2
"""
    chunks = parse_diff(diff, context_lines=5)
    assert len(chunks) == 1
    # Unchanged lines (space-prefixed) should appear in context_lines
    assert any("context_before_1" in l for l in chunks[0].context_lines)
    assert any("context_after_1" in l for l in chunks[0].context_lines)
    # Changed lines should only contain + / - lines
    assert all(l.startswith(("+", "-")) for l in chunks[0].changed_lines)


def test_never_raises_on_garbage():
    garbage_inputs = [
        "}{not a diff at all",
        "@@ broken header",
        "+++ b/file.java with no header",
        "--- a\n+++ b\n@@ @@\n" + "\n".join(f"+line{i}" for i in range(500)),
    ]
    for raw in garbage_inputs:
        result = parse_diff(raw)
        assert isinstance(result, list)


def test_chunk_dataclass_fields():
    chunks = parse_diff(SINGLE_FILE_DIFF)
    c = chunks[0]
    assert isinstance(c.file, str)
    assert isinstance(c.hunk_header, str)
    assert isinstance(c.changed_lines, list)
    assert isinstance(c.context_lines, list)
