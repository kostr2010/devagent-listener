from app.diff.models.diff import Diff, DiffSummary

DIFF = Diff(
    remote="gitcode.com",
    project="openharmony/arkcompiler_runtime_core",
    files=list(),
    summary=DiffSummary(
        total_files=0,
        added_lines=0,
        removed_lines=0,
        base_sha="master",
        head_sha="master",
    ),
)
