import unittest
import tempfile
import os
import subprocess

from app.devagent.stages.review_init import (
    populate_workdir,
    extract_project_info,
    ProjectInfo,
)
from tests.devagent.mock.test_diffs.basic.arkcompiler_ets_frontend.empty import (
    DIFF as FE_EMPTY,
)
from tests.devagent.mock.test_diffs.basic.arkcompiler_runtime_core.empty import (
    DIFF as RT_EMPTY,
)


class PopulateWorkdirTest(unittest.TestCase):
    def test_no_diffs(self) -> None:
        with tempfile.TemporaryDirectory() as wd:
            populate_workdir(
                wd,
                ProjectInfo(
                    remote="gitcode.com",
                    project="nazarovkonstantin/arkcompiler_development_rules",
                    revision="main",
                ),
                list(),
            )

            self._check_dev_rules_project(wd)

            wd_content = os.listdir(wd)
            self.assertListEqual(sorted(wd_content), sorted(["review_rules"]))

    def test_several_empty_diffs(self) -> None:
        with tempfile.TemporaryDirectory() as wd:
            populate_workdir(
                wd,
                ProjectInfo(
                    remote="gitcode.com",
                    project="nazarovkonstantin/arkcompiler_development_rules",
                    revision="main",
                ),
                [extract_project_info(diff) for diff in [RT_EMPTY, FE_EMPTY]],
            )

            self._check_dev_rules_project(wd)

            wd_content = os.listdir(wd)
            self.assertListEqual(
                sorted(wd_content),
                sorted(["review_rules", "openharmony"]),
            )
            openharmony_content = os.listdir(os.path.join(wd, "openharmony"))
            self.assertListEqual(
                sorted(openharmony_content),
                sorted(["arkcompiler_runtime_core", "arkcompiler_ets_frontend"]),
            )
            arkcompiler_ets_frontend_root = os.path.join(
                os.path.join(wd, "openharmony", "arkcompiler_ets_frontend")
            )
            self.assertEqual(_get_revision(arkcompiler_ets_frontend_root), "master")
            arkcompiler_runtime_core_root = os.path.join(
                os.path.join(wd, "openharmony", "arkcompiler_runtime_core")
            )
            self.assertEqual(_get_revision(arkcompiler_runtime_core_root), "master")

    def _check_dev_rules_project(self, wd: str) -> None:
        dev_rules_root = os.path.abspath(os.path.join(wd, "review_rules"))
        self.assertTrue(os.path.exists(dev_rules_root))


def _get_revision(root: str) -> str:
    cmd = ["git", "-C", root, "rev-parse", "--abbrev-ref", "HEAD"]

    res = subprocess.run(
        cmd,
        capture_output=True,
    )

    assert (
        res.returncode == 0
    ), f"Return code of cmd {cmd} was {res.returncode}. expected 0"
    stdout = res.stdout.decode("utf-8")

    return stdout.strip()


if __name__ == "__main__":
    unittest.main()
