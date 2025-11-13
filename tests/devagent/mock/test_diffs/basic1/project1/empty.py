from app.gitcode.get_diff import Diff, Summary, DiffFile

DIFF = Diff(
    project="project1",
    pr_number=1,
    files=list(),
    summary=Summary(
        total_files=0,
        added_lines=0,
        removed_lines=0,
        base_sha="95ba5f0054d73884e12b0e9c6c90c18f7278d054",
        head_sha="95ba5f0054d73884e12b0e9c6c90c18f7278d054",
    ),
)
