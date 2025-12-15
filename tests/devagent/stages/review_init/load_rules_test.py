import unittest
import os


from app.devagent.stages.review_init import load_rules, DevagentRule


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

    def test_non_existing_rule(self) -> None:
        """load_rules throws an exception if loaded rule does not exist"""
        wd = _get_wd("non_existing_rule_in_config")
        with self.assertRaises(AssertionError) as e:
            load_rules(wd)
        self.assertTrue("Rule does not exist" in str(e.exception))

    def test_non_existing_dir(self) -> None:
        """load_rules does not filter out directories that were not found in the source tree"""
        wd = _get_wd("non_existing_dir_in_config")
        rules = load_rules(wd)
        ans = [
            DevagentRule(name="rule2.md", dirs=["project1", "project2/dir1"]),
            DevagentRule(name="rule1.md", dirs=["project1"]),
        ]
        self.assertListEqual(
            [rule.model_dump() for rule in rules],
            [rule.model_dump() for rule in ans],
        )

    def test_duplicate_rule_in_config(self) -> None:
        """load_rules throws an exception if there are duplicate rules in the config"""
        wd = _get_wd("duplicate_rule_in_config")
        with self.assertRaises(AssertionError) as e:
            load_rules(wd)
        self.assertTrue(
            "Loaded rules have duplicates, please check" in str(e.exception)
        )

    def test_basic(self) -> None:
        wd = _get_wd("basic")
        rules = load_rules(wd)
        ans = list[DevagentRule]()
        self.assertListEqual(
            [rule.model_dump() for rule in rules],
            [rule.model_dump() for rule in ans],
        )

    def test_basic1(self) -> None:
        """load_rules discards the disabled rules"""
        wd = _get_wd("basic1")
        rules = load_rules(wd)
        ans = [
            DevagentRule(name="rule1.md", dirs=["project1/dir1/", "project2/dir1"]),
            DevagentRule(name="rule2.md", dirs=["project2", "project2/dir3/"]),
            DevagentRule(
                name="rule3.md",
                dirs=["project1/dir2", "project2/dir3"],
                skip=["project2/dir3/dir"],
            ),
            DevagentRule(name="rule4.md", dirs=["project1/dir2", "project2/dir4"]),
        ]
        self.assertListEqual(
            [rule.model_dump() for rule in rules],
            [rule.model_dump() for rule in ans],
        )


if __name__ == "__main__":
    unittest.main()
