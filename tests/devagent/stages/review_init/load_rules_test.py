import unittest
import os


from app.devagent.stages.review_init import load_rules


def _get_wd(wd_name: str) -> str:
    cur_dir = os.path.dirname(os.path.realpath(__file__))
    wd = os.path.normpath(
        os.path.join(cur_dir, "..", "..", "mock", "test_workdirs", wd_name)
    )
    return wd


class LoadRulesTest(unittest.TestCase):
    def test_non_existing_wd(self) -> None:
        """load_rules throws an exception if wd does not contain project with development rules"""
        wd = _get_wd("non_existing_wd")
        with self.assertRaises(AssertionError) as e:
            load_rules(wd)
        self.assertTrue("No project root" in str(e.exception))

    def test_no_config(self) -> None:
        """load_rules throws an exception if no config for rules exists in the wd"""
        wd = _get_wd("no_rules_config")
        with self.assertRaises(AssertionError) as e:
            load_rules(wd)
        self.assertTrue("No config file" in str(e.exception))

    def test_no_rules_folder(self) -> None:
        """load_rules throws an exception if no directory with rules exists in the wd"""
        wd = _get_wd("no_rules_folder")
        with self.assertRaises(AssertionError) as e:
            load_rules(wd)
        self.assertTrue("No rules dir" in str(e.exception))

    def test_non_existing_rule(self) -> None:
        """load_rules throws an exception if loaded rule does not exist"""
        wd = _get_wd("non_existing_rule_in_config")
        with self.assertRaises(AssertionError) as e:
            load_rules(wd)
        self.assertTrue("No rule" in str(e.exception))

    def test_non_existing_dir(self) -> None:
        """load_rules filters out all directories that were not found in the source tree"""
        wd = _get_wd("non_existing_dir_in_config")
        rules = load_rules(wd)
        ans = {
            os.path.join(wd, "project1"): [
                os.path.join(
                    wd,
                    "nazarovkonstantin",
                    "arkcompiler_development_rules",
                    "REVIEW_RULES",
                    "rule2.md",
                )
            ],
        }
        self.assertDictEqual(rules, ans)

    def test_basic(self) -> None:
        wd = _get_wd("basic")
        rules = load_rules(wd)
        ans = dict[str, list[str]]()
        self.assertDictEqual(rules, ans)

    def test_basic1(self) -> None:
        wd = _get_wd("basic1")
        rules = load_rules(wd)
        ans = {
            os.path.join(wd, "project1", "dir1"): [
                os.path.join(
                    wd,
                    "nazarovkonstantin",
                    "arkcompiler_development_rules",
                    "REVIEW_RULES",
                    "rule1.md",
                )
            ],
            os.path.join(wd, "project1", "dir2"): [
                os.path.join(
                    wd,
                    "nazarovkonstantin",
                    "arkcompiler_development_rules",
                    "REVIEW_RULES",
                    "rule2.md",
                ),
                os.path.join(
                    wd,
                    "nazarovkonstantin",
                    "arkcompiler_development_rules",
                    "REVIEW_RULES",
                    "rule3.md",
                ),
            ],
            os.path.join(wd, "project2", "dir1"): [
                os.path.join(
                    wd,
                    "nazarovkonstantin",
                    "arkcompiler_development_rules",
                    "REVIEW_RULES",
                    "rule1.md",
                )
            ],
            os.path.join(wd, "project2"): [
                os.path.join(
                    wd,
                    "nazarovkonstantin",
                    "arkcompiler_development_rules",
                    "REVIEW_RULES",
                    "rule2.md",
                )
            ],
            os.path.join(wd, "project2", "dir3"): [
                os.path.join(
                    wd,
                    "nazarovkonstantin",
                    "arkcompiler_development_rules",
                    "REVIEW_RULES",
                    "rule1.md",
                ),
                os.path.join(
                    wd,
                    "nazarovkonstantin",
                    "arkcompiler_development_rules",
                    "REVIEW_RULES",
                    "rule2.md",
                ),
                os.path.join(
                    wd,
                    "nazarovkonstantin",
                    "arkcompiler_development_rules",
                    "REVIEW_RULES",
                    "rule3.md",
                ),
            ],
        }
        self.assertDictEqual(rules, ans)
