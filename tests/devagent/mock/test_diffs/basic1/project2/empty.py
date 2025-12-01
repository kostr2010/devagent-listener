from app.diff.models.diff import Diff, DiffSummary, DiffFile

DIFF = Diff(
    remote="",
    project="project2",
    files=list(),
    summary=DiffSummary(
        total_files=0,
        added_lines=0,
        removed_lines=0,
        base_sha="3736fb15c8710284110d8d2d2d5be10311e2e684",
        head_sha="3736fb15c8710284110d8d2d2d5be10311e2e684",
    ),
)
