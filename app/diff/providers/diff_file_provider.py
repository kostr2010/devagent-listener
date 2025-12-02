import os.path
import unidiff

from app.diff.models.diff import Diff, DiffFile, DiffSummary
from app.diff.provider import IDiffProvider


class DiffFileDiffProvider(IDiffProvider):
    def __init__(self) -> None:
        super().__init__()

    def domain(self) -> str:
        # to accept paths that start with /
        return ""

    def get_diff(self, url: str) -> Diff:
        _assert_valid_url(url)

        patchset = unidiff.PatchSet.from_filename(url)

        patch_files = (
            patchset.added_files + patchset.removed_files + patchset.modified_files
        )

        return Diff(
            remote="",
            project="",
            summary=DiffSummary(
                total_files=len(patch_files),
                added_lines=patchset.added,
                removed_lines=patchset.removed,
                base_sha="",
                head_sha="",
            ),
            files=[
                DiffFile(
                    file=patch_file.path,
                    diff=str(patch_file),
                    added_lines=patch_file.added,
                    removed_lines=patch_file.removed,
                )
                for patch_file in patch_files
            ],
        )


###########
# private #
###########


def _assert_valid_url(url: str) -> None:
    if not os.path.exists(url):
        raise Exception(f"Invalid diff file path : {url}")
