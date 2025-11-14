import unittest
import shutil
import os

from app.devagent.stages.review_init import load_rules, prepare_tasks
from app.devagent.stages.review_init import (
    _map_applicable_rules_to_diffs,
    _generate_patch_context,
)

from tests.devagent.mock.test_diffs.basic.arkcompiler_ets_frontend.empty import (
    DIFF as FE_EMPTY,
)
from tests.devagent.mock.test_diffs.basic.arkcompiler_runtime_core.empty import (
    DIFF as RT_EMPTY,
)
from tests.devagent.mock.test_diffs.basic1.project1.empty import (
    DIFF as P1_EMPTY,
)
from tests.devagent.mock.test_diffs.basic1.project1.diff1 import (
    DIFF as P1_DIFF1,
)
from tests.devagent.mock.test_diffs.basic1.project2.empty import (
    DIFF as P2_EMPTY,
)
from tests.devagent.mock.test_diffs.basic1.project2.diff1 import (
    DIFF as P2_DIFF1,
)


def _get_wd(wd_name: str) -> str:
    cur_dir = os.path.dirname(os.path.realpath(__file__))
    wd = os.path.normpath(
        os.path.join(cur_dir, "..", "..", "mock", "test_workdirs", wd_name)
    )
    return wd


def _clean_wd(wd: str) -> None:
    shutil.rmtree(os.path.join(wd, ".content.d"), ignore_errors=True)
    shutil.rmtree(os.path.join(wd, ".context.d"), ignore_errors=True)


class PrepareTasksTest(unittest.TestCase):
    def test_basic(self) -> None:
        task_id = f"task_id_{__name__}"
        # diffs = get_diffs(urls)
        diffs = [FE_EMPTY, RT_EMPTY]
        # populate_workdir(wd, diffs)
        wd = _get_wd("basic")
        rules = load_rules(wd)
        tasks = prepare_tasks(task_id, wd, rules, diffs)
        self.assertListEqual(tasks, list())
        _clean_wd(wd)

    def test_basic1_empty(self) -> None:
        task_id = f"task_id_{__name__}"
        # diffs = get_diffs(urls)
        diffs = [P1_EMPTY, P2_EMPTY]
        # populate_workdir(wd, diffs)
        wd = _get_wd("basic1")
        rules = load_rules(wd)
        tasks = prepare_tasks(task_id, wd, rules, diffs)
        self.assertListEqual(tasks, list())
        _clean_wd(wd)

    def test_basic1_p1_diff1(self) -> None:
        task_id = f"task_id_{__name__}"
        # diffs = get_diffs(urls)
        diffs = [P1_DIFF1]
        # populate_workdir(wd, diffs)
        wd = _get_wd("basic1")
        rules = load_rules(wd)
        tasks = prepare_tasks(task_id, wd, rules, diffs)
        self.assertEqual(len(tasks), 3)
        for task in tasks:
            self.assertEqual(task.wd, wd)
            self.assertEqual(task.project, P1_DIFF1.project)
            self.assertEqual(wd, os.path.commonpath([wd, task.patch_path]))
            with open(task.patch_path) as patch:
                gold = "\n\n".join([file.diff for file in P1_DIFF1.files])
                self.assertEqual(patch.read(), gold)
            self.assertEqual(wd, os.path.commonpath([wd, task.context_path]))
            with open(task.context_path) as context:
                gold = _generate_patch_context(task.patch_path)
                self.assertEqual(context.read(), gold)
            self.assertTrue(os.path.exists(task.rule_path))
            self.assertListEqual(
                rules[os.path.basename(task.rule_path)], task.rule_dirs
            )
        task_rules = [os.path.basename(task.rule_path) for task in tasks]
        self.assertListEqual(
            sorted(task_rules), sorted(["rule4.md", "rule3.md", "rule1.md"])
        )
        _clean_wd(wd)

    def test_basic1_p2_diff1(self) -> None:
        task_id = f"task_id_{__name__}"
        # diffs = get_diffs(urls)
        diffs = [P2_DIFF1]
        # populate_workdir(wd, diffs)
        wd = _get_wd("basic1")
        rules = load_rules(wd)
        tasks = prepare_tasks(task_id, wd, rules, diffs)
        self.assertEqual(len(tasks), 3)
        for task in tasks:
            self.assertEqual(task.wd, wd)
            self.assertEqual(task.project, P2_DIFF1.project)
            self.assertEqual(wd, os.path.commonpath([wd, task.patch_path]))
            with open(task.patch_path) as patch:
                gold = "\n\n".join([file.diff for file in P2_DIFF1.files])
                self.assertEqual(patch.read(), gold)
            self.assertEqual(wd, os.path.commonpath([wd, task.context_path]))
            with open(task.context_path) as context:
                gold = _generate_patch_context(task.patch_path)
                self.assertEqual(context.read(), gold)
            self.assertTrue(os.path.exists(task.rule_path))
            self.assertListEqual(
                rules[os.path.basename(task.rule_path)], task.rule_dirs
            )
        task_rules = [os.path.basename(task.rule_path) for task in tasks]
        self.assertListEqual(
            sorted(task_rules), sorted(["rule3.md", "rule2.md", "rule1.md"])
        )
        _clean_wd(wd)

    def test_basic1_diff1(self) -> None:
        task_id = f"task_id_{__name__}"
        # diffs = get_diffs(urls)
        diffs = [P1_DIFF1, P2_DIFF1]
        # populate_workdir(wd, diffs)
        wd = _get_wd("basic1")
        rules = load_rules(wd)
        tasks = prepare_tasks(task_id, wd, rules, diffs)
        self.assertEqual(len(tasks), 6)
        project_to_diff = {
            P2_DIFF1.project: "\n\n".join([file.diff for file in P2_DIFF1.files]),
            P1_DIFF1.project: "\n\n".join([file.diff for file in P1_DIFF1.files]),
        }
        for task in tasks:
            self.assertEqual(task.wd, wd)
            self.assertEqual(wd, os.path.commonpath([wd, task.patch_path]))
            with open(task.patch_path) as patch:
                gold = project_to_diff[task.project]
                self.assertEqual(patch.read(), gold)
            self.assertEqual(wd, os.path.commonpath([wd, task.context_path]))
            with open(task.context_path) as context:
                gold = _generate_patch_context(task.patch_path)
                self.assertEqual(context.read(), gold)
            self.assertTrue(os.path.exists(task.rule_path))
            self.assertListEqual(
                rules[os.path.basename(task.rule_path)], task.rule_dirs
            )
        task_rules = [os.path.basename(task.rule_path) for task in tasks]
        self.assertListEqual(
            sorted(task_rules),
            sorted(
                ["rule4.md", "rule3.md", "rule1.md", "rule3.md", "rule2.md", "rule1.md"]
            ),
        )
        _clean_wd(wd)


class MapApplicableRulesToDiffsTest(unittest.TestCase):
    def test_basic_empty(self) -> None:
        wd = _get_wd("basic")
        rules = load_rules(wd)

        res = _map_applicable_rules_to_diffs(rules, RT_EMPTY)
        ans = dict[str, str]()
        self.assertDictEqual(res, ans)

        res = _map_applicable_rules_to_diffs(rules, FE_EMPTY)
        ans = dict[str, str]()
        self.assertDictEqual(res, ans)

    def test_basic1_empty(self) -> None:
        wd = _get_wd("basic1")
        rules = load_rules(wd)

        res = _map_applicable_rules_to_diffs(rules, P1_EMPTY)
        ans = dict[str, str]()
        self.assertDictEqual(res, ans)

        res = _map_applicable_rules_to_diffs(rules, P2_EMPTY)
        ans = dict[str, str]()
        self.assertDictEqual(res, ans)

    def test_basic1_p1_diff1(self) -> None:
        wd = _get_wd("basic1")
        rules = load_rules(wd)
        project1_combined_diff = "\n\n".join([file.diff for file in P1_DIFF1.files])
        res = _map_applicable_rules_to_diffs(rules, P1_DIFF1)
        ans = {
            "rule1.md": project1_combined_diff,
            "rule3.md": project1_combined_diff,
            "rule4.md": project1_combined_diff,
        }
        self.assertDictEqual(res, ans)

    def test_basic1_2_diff1(self) -> None:
        wd = _get_wd("basic1")
        rules = load_rules(wd)
        project2_combined_diff = "\n\n".join([file.diff for file in P2_DIFF1.files])
        res = _map_applicable_rules_to_diffs(rules, P2_DIFF1)
        ans = {
            "rule1.md": project2_combined_diff,
            "rule2.md": project2_combined_diff,
            "rule3.md": project2_combined_diff,
        }
        self.assertDictEqual(res, ans)


if __name__ == "__main__":
    unittest.main()
