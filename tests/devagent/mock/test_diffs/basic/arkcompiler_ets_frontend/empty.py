from app.gitcode.get_diff import Diff, Summary

DIFF = Diff(
    project="openharmony/arkcompiler_ets_frontend",
    pr_number=1111,
    files=list(),
    summary=Summary(
        total_files=0,
        added_lines=0,
        removed_lines=0,
        base_sha="master",
        head_sha="master",
    ),
)
