import unittest
import shutil
import tempfile
import os
import os.path

from app.devagent.infrastructure import (
    DEVAGENT_REVIEW_RULES_CONFIG,
    DEVAGENT_REVIEW_RULES_DIR,
)

from app.devagent.infrastructure import (
    load_rules,
)  # , _load_rules_from_repo_root, _load_rules_from_config


class LoadRulesTestCase:
    def __init__(self):
        self.mapping = {}

    def add_repo(self, repo: str, config: str, rules: list, answer: dict):
        self.mapping.update({repo: (config, rules, answer)})

    def get_answer(self, workdir: str):
        ans = {}

        for repo, tup in self.mapping.items():
            _, _, answer = tup
            repo_abspath = os.path.abspath(os.path.join(workdir, repo))
            rules_abspath = os.path.abspath(
                os.path.join(repo_abspath, DEVAGENT_REVIEW_RULES_DIR)
            )
            answer_abspath = {}
            for dir, rules in answer.items():
                dir_abspath = os.path.abspath(os.path.join(repo_abspath, dir))
                rules_abspath = [
                    os.path.abspath(os.path.join(rules_abspath, rule)) for rule in rules
                ]
                answer_abspath.update({dir_abspath: sorted(rules_abspath)})
            ans.update({repo_abspath: answer_abspath})

        return ans


class LoadRulesTestCaseEnv:
    def __init__(self, test_case: LoadRulesTestCase, repo_struct: dict):
        self.test_case = test_case
        self.repo_struct = repo_struct

    def get_wd(self):
        return self.wd

    def __enter__(self):
        self.wd = tempfile.mkdtemp()

        for repo, test_info in self.test_case.mapping.items():
            config, rules, _ = test_info
            repo_root = os.path.abspath(os.path.join(self.wd, repo))
            os.mkdir(repo_root)
            for dir in self.repo_struct.get(repo, []):
                abspath = os.path.join(repo_root, dir)
                os.makedirs(abspath, exist_ok=True)
            rules_dir = os.path.join(repo_root, DEVAGENT_REVIEW_RULES_DIR)
            os.makedirs(rules_dir, exist_ok=True)
            for rule in rules:
                rule_abspath = os.path.abspath(os.path.join(rules_dir, rule))
                with open(rule_abspath, "w", encoding="utf-8") as r:
                    r.write(rule)
            rules_cfg = os.path.abspath(
                os.path.join(repo_root, DEVAGENT_REVIEW_RULES_CONFIG)
            )
            with open(rules_cfg, "w", encoding="utf-8") as cfg:
                cfg.write(config)

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
        for variant in empty_config_variants:
            test = LoadRulesTestCase()
            test.add_repo("repo1", variant, ["rule1.md", "rule2.md", "rule3.md"], {})
            test.add_repo("repo2", variant, ["rule1.md"], {})
            test.add_repo("repo3", variant, [], {})

            self._test_load_rules(test, {})

    def test_config_1(self):
        config_variants = [
            """
dir1 rule1.md
            """,
            """
dir1/ rule1.md
            """,
            """
dir1  rule1.md
dir1/ rule1.md
            """,
            """
dir1  rule1.md
#dir2 rule2.md
            """,
        ]
        for variant in config_variants:
            test = LoadRulesTestCase()
            test.add_repo(
                "repo1",
                variant,
                ["rule1.md", "rule2.md", "rule3.md"],
                {"dir1": ["rule1.md"]},
            )
            test.add_repo(
                "repo2", variant, ["rule1.md", "rule3.md"], {"dir1": ["rule1.md"]}
            )
            test.add_repo("repo3", variant, ["rule1.md"], {"dir1": ["rule1.md"]})

            self._test_load_rules(
                test,
                {
                    "repo1": ["dir1"],
                    "repo2": ["dir1", "dir2"],
                    "repo3": ["dir1", "dir3"],
                },
            )

    def test_config_2(self):
        config_variants = [
            """
dir1 rule1.md
dir1 rule3.md
            """,
            """
dir1/ rule1.md rule3.md
            """,
            """
dir1  rule1.md rule3.md
dir1/ rule3.md
            """,
            """
dir1  rule1.md rule3.md
#dir2 rule2.md
            """,
        ]
        answer = {"dir1": ["rule1.md", "rule3.md"]}
        for variant in config_variants:
            test = LoadRulesTestCase()
            test.add_repo(
                "repo1",
                variant,
                ["rule1.md", "rule2.md", "rule3.md"],
                answer,
            )
            test.add_repo("repo2", variant, ["rule1.md", "rule3.md"], answer)
            test.add_repo(
                "repo3", variant, ["rule1.md", "rule3.md", "rule2.md"], answer
            )

            self._test_load_rules(
                test,
                {
                    "repo1": ["dir1"],
                    "repo2": ["dir1", "dir2", "dir3"],
                    "repo3": ["dir1", "dir3"],
                },
            )


if __name__ == "__main__":
    unittest.main()
