import unittest
import shutil
import tempfile
import os
import os.path

from app.devagent.infrastructure import (
    DEVAGENT_RULES_REPO,
    DEVAGENT_REVIEW_RULES_CONFIG,
    DEVAGENT_REVIEW_RULES_DIR,
)

from app.devagent.infrastructure import (
    load_rules,
)  # , _load_rules_from_repo_root, _load_rules_from_config


class LoadRulesTestCase:
    def __init__(self, cfg: str, existing_rules: list, answer: dict):
        self.cfg = cfg
        self.rules = existing_rules
        self.answer = answer

    def get_answer(self, workdir: str):
        ans = {}

        rules_repo = os.path.abspath(os.path.join(workdir, DEVAGENT_RULES_REPO))
        rules_dir = os.path.abspath(os.path.join(rules_repo, DEVAGENT_REVIEW_RULES_DIR))

        for dir, rules in self.answer.items():
            dir_abspath = os.path.abspath(os.path.join(workdir, dir))
            rules_abspath = [
                os.path.abspath(os.path.join(rules_dir, rule)) for rule in rules
            ]
            ans.update({dir_abspath: sorted(rules_abspath)})

        return ans


class LoadRulesTestCaseEnv:
    def __init__(self, test_case: LoadRulesTestCase, repo_struct: dict):
        self.test_case = test_case
        self.repo_struct = repo_struct

    def get_wd(self):
        return self.wd

    def __enter__(self):
        self.wd = tempfile.mkdtemp()

        rules_repo_root = os.path.abspath(os.path.join(self.wd, DEVAGENT_RULES_REPO))
        os.makedirs(rules_repo_root, exist_ok=True)
        rules_dir = os.path.abspath(
            os.path.join(rules_repo_root, DEVAGENT_REVIEW_RULES_DIR)
        )
        os.makedirs(rules_dir, exist_ok=True)
        for rule in self.test_case.rules:
            rule_abspath = os.path.abspath(os.path.join(rules_dir, rule))
            with open(rule_abspath, "w", encoding="utf-8") as r:
                r.write("text")

        rules_cfg = os.path.abspath(
            os.path.join(rules_repo_root, DEVAGENT_REVIEW_RULES_CONFIG)
        )
        with open(rules_cfg, "w", encoding="utf-8") as cfg:
            cfg.write(self.test_case.cfg)

        for repo, dirs in self.repo_struct.items():
            for dir in dirs:
                dir_abspath = os.path.abspath(os.path.join(self.wd, repo, dir))
                os.makedirs(dir_abspath, exist_ok=True)

        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        shutil.rmtree(self.wd, ignore_errors=True)


class LoadRulesTest(unittest.TestCase):
    def _test_load_rules(self, test_case: LoadRulesTestCase, repo_struct: dict):
        with LoadRulesTestCaseEnv(test_case, repo_struct) as env:
            wd = env.get_wd()
            ans = test_case.get_answer(wd)
            res = load_rules(wd)
            self.assertDictEqual(ans, res)

    def test_empty_config(self):
        empty_config_variants = [
            "",
            "\n",
            " \n \n",
            "\n  # kekeke \n",
            "# this is empty \n    \n  ",
        ]
        repo_struct = {}
        answer = {}
        for variant in empty_config_variants:
            test = LoadRulesTestCase(
                variant, ["rule1.md", "rule2.md", "rule3.md"], answer
            )
            self._test_load_rules(test, repo_struct)

            test = LoadRulesTestCase(variant, ["rule1.md"], answer)
            self._test_load_rules(test, repo_struct)

            test = LoadRulesTestCase(variant, [], answer)
            self._test_load_rules(test, repo_struct)

    def test_config_1(self):
        config_variants = [
            """
repo1/dir1 rule1.md
            """,
            """
repo1/dir1/ rule1.md
            """,
            """
repo1/dir1  rule1.md
repo1/dir1/ rule1.md
            """,
            """
repo1/dir1  rule1.md
#repo1/dir2 rule2.md
            """,
        ]
        repo_struct = {
            "repo1": ["dir1"],
            "repo2": ["dir1", "dir2"],
            "repo3": ["dir1", "dir3"],
        }
        answer = {"repo1/dir1": ["rule1.md"]}
        for variant in config_variants:
            test = LoadRulesTestCase(
                variant,
                ["rule1.md", "rule2.md", "rule3.md"],
                answer,
            )
            self._test_load_rules(test, repo_struct)

            test = LoadRulesTestCase(
                variant,
                ["rule1.md", "rule3.md"],
                answer,
            )
            self._test_load_rules(test, repo_struct)

            test = LoadRulesTestCase(
                variant,
                ["rule1.md"],
                answer,
            )
            self._test_load_rules(test, repo_struct)

    def test_config_2(self):
        config_variants = [
            """
repo1/dir1 rule1.md
repo1/dir1 rule3.md
            """,
            """
repo1/dir1/ rule1.md rule3.md
            """,
            """
repo1/dir1  rule1.md rule3.md
repo1/dir1/ rule3.md
            """,
            """
repo1/dir1  rule1.md rule3.md
#repo1/dir2 rule2.md
            """,
        ]
        repo_struct = {
            "repo1": ["dir1"],
            "repo2": ["dir1", "dir2", "dir3"],
            "repo3": ["dir1", "dir3"],
        }
        answer = {"repo1/dir1": ["rule1.md", "rule3.md"]}
        for variant in config_variants:
            test = LoadRulesTestCase(
                variant, ["rule1.md", "rule2.md", "rule3.md"], answer
            )
            self._test_load_rules(test, repo_struct)

            test = LoadRulesTestCase(variant, ["rule1.md", "rule3.md"], answer)
            self._test_load_rules(test, repo_struct)


if __name__ == "__main__":
    unittest.main()
