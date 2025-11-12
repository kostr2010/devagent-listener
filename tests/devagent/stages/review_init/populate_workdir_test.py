import unittest
import tempfile
import os
import subprocess

from app.devagent.stages.review_init import populate_workdir
from app.config import CONFIG
from tests.devagent.mock.test_diffs import (
    OPENHARMONY_ARCKOMPILER_RUNTIME_CORE_EMPTY,
    OPENHARMONY_ARCKOMPILER_ETS_FRONTEND_EMPTY,
)


class PopulateWorkdirTest(unittest.TestCase):
    def test_no_diffs(self) -> None:
        with tempfile.TemporaryDirectory() as wd:
            populate_workdir(wd, list())

            self._check_dev_rules_project(wd)
            self._check_devagent_toml(wd)

            wd_content = os.listdir(wd)
            self.assertListEqual(wd_content, ["nazarovkonstantin", ".devagent.toml"])

    def test_several_empty_diffs(self) -> None:
        with tempfile.TemporaryDirectory() as wd:
            populate_workdir(
                wd,
                [
                    OPENHARMONY_ARCKOMPILER_RUNTIME_CORE_EMPTY,
                    OPENHARMONY_ARCKOMPILER_ETS_FRONTEND_EMPTY,
                ],
            )

            self._check_dev_rules_project(wd)
            self._check_devagent_toml(wd)

            wd_content = os.listdir(wd)
            self.assertListEqual(
                wd_content, ["nazarovkonstantin", ".devagent.toml", "openharmony"]
            )
            openharmony_content = os.listdir(os.path.join(wd, "openharmony"))
            self.assertListEqual(
                openharmony_content,
                ["arkcompiler_runtime_core", "arkcompiler_ets_frontend"],
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
        dev_rules_root = os.path.abspath(
            os.path.join(wd, "nazarovkonstantin", "arkcompiler_development_rules")
        )
        self.assertTrue(os.path.exists(dev_rules_root))

    def _check_devagent_toml(self, wd: str) -> None:
        devagent_toml = os.path.abspath(os.path.join(wd, ".devagent.toml"))
        self.assertTrue(os.path.exists(devagent_toml))
        with open(devagent_toml) as cfg:
            content = cfg.read()

            ans = ""
            ans += f'provider = "{CONFIG.DEVAGENT_PROVIDER}"\n'
            ans += f'model = "{CONFIG.DEVAGENT_MODEL}"\n'
            ans += f'api_key = "{CONFIG.DEVAGENT_API_KEY}"\n'
            ans += f"auto_approve_code = false\n"

            self.assertEqual(content, ans)


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
