from app.diff.models.diff import Diff, DiffSummary, DiffFile

DIFF = Diff(
    remote="",
    project="project1",
    files=list(),
    summary=DiffSummary(
        total_files=0,
        added_lines=0,
        removed_lines=0,
        base_sha="95ba5f0054d73884e12b0e9c6c90c18f7278d054",
        head_sha="95ba5f0054d73884e12b0e9c6c90c18f7278d054",
    ),
)
