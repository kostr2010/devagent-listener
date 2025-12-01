from app.diff.models.diff import Diff, DiffSummary, DiffFile

DIFF = Diff(
    remote="",
    project="project1",
    files=[
        DiffFile(
            file="dir1/file1",
            diff="""
diff --git a/dir1/file1 b/dir1/file1
index e69de29..7c4a013 100644
--- a/dir1/file1
+++ b/dir1/file1
@@ -0,0 +1 @@
+aaa
\ No newline at end of file
""",
            added_lines=1,
            removed_lines=0,
        ),
        DiffFile(
            file="dir2/file1",
            diff="""
diff --git a/dir2/file1 b/dir2/file1
index e69de29..01f02e3 100644
--- a/dir2/file1
+++ b/dir2/file1
@@ -0,0 +1 @@
+bbb
\ No newline at end of file
""",
            added_lines=1,
            removed_lines=0,
        ),
        DiffFile(
            file="new_file",
            diff="""
diff --git a/new_file b/new_file
new file mode 100644
index 0000000..2383bd5
--- /dev/null
+++ b/new_file
@@ -0,0 +1 @@
+ccc
\ No newline at end of file
""",
            added_lines=1,
            removed_lines=0,
        ),
    ],
    summary=DiffSummary(
        total_files=3,
        added_lines=3,
        removed_lines=0,
        base_sha="95ba5f0054d73884e12b0e9c6c90c18f7278d054",
        head_sha="46b71619e5ae3dc8aa00aa561315dff329811002",
    ),
)
