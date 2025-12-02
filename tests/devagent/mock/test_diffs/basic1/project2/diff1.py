from app.diff.models.diff import Diff, DiffSummary, DiffFile

DIFF = Diff(
    remote="",
    project="project2",
    files=[
        DiffFile(
            file="dir1/file2",
            diff="""
diff --git a/dir1/file1 b/dir1/file2
similarity index 100%
rename from dir1/file1
rename to dir1/file2
""",
            added_lines=0,
            removed_lines=0,
        ),
        DiffFile(
            file="dir3/file1",
            diff="""
diff --git a/dir3/file1 b/dir3/file1
deleted file mode 100644
index e69de29..0000000
""",
            added_lines=0,
            removed_lines=0,
        ),
        DiffFile(
            file="file3",
            diff="""
diff --git a/file3 b/file3
new file mode 100644
index 0000000..7c4a013
--- /dev/null
+++ b/file3
@@ -0,0 +1 @@
+aaa
\ No newline at end of file
""",
            added_lines=1,
            removed_lines=0,
        ),
    ],
    summary=DiffSummary(
        total_files=3,
        added_lines=1,
        removed_lines=0,
        base_sha="3736fb15c8710284110d8d2d2d5be10311e2e684",
        head_sha="c6df4c5a535aac16e0f86c308fd6eaef2213e6f1",
    ),
)
