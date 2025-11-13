import unittest
import os

from app.devagent.stages.review_init import prepare_tasks


def _get_wd(wd_name: str) -> str:
    cur_dir = os.path.dirname(os.path.realpath(__file__))
    wd = os.path.normpath(
        os.path.join(cur_dir, "..", "..", "mock", "test_workdirs", wd_name)
    )
    return wd


class PrepareTasksTest(unittest.TestCase):
    pass


from app.devagent.stages.review_init import load_rules
from app.devagent.stages.review_init import _map_applicable_rules_to_diffs
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


class MapApplicableRulesToDiffsTest(unittest.TestCase):
    def test_basic_empty_diff(self) -> None:
        wd = _get_wd("basic")
        rules = load_rules(wd)
        diffs = [RT_EMPTY]
        res = _map_applicable_rules_to_diffs(wd, rules, diffs)
        ans = {
            os.path.join(wd, "openharmony/arkcompiler_runtime_core"): dict[str, str]()
        }
        self.assertDictEqual(res, ans)

    def test_basic_empty_diffs(self) -> None:
        wd = _get_wd("basic")
        rules = load_rules(wd)
        diffs = [RT_EMPTY, FE_EMPTY]
        res = _map_applicable_rules_to_diffs(wd, rules, diffs)
        ans = {
            os.path.join(wd, "openharmony/arkcompiler_runtime_core"): dict[str, str](),
            os.path.join(wd, "openharmony/arkcompiler_ets_frontend"): dict[str, str](),
        }
        self.assertDictEqual(res, ans)

    def test_basic1_empty_diff(self) -> None:
        wd = _get_wd("basic1")
        rules = load_rules(wd)
        diffs = [P1_EMPTY]
        res = _map_applicable_rules_to_diffs(wd, rules, diffs)
        ans = {os.path.join(wd, "project1"): dict[str, str]()}
        self.assertDictEqual(res, ans)

    def test_basic1_empty_diffs(self) -> None:
        wd = _get_wd("basic1")
        rules = load_rules(wd)
        diffs = [P1_EMPTY, P2_EMPTY]
        res = _map_applicable_rules_to_diffs(wd, rules, diffs)
        ans = {
            os.path.join(wd, "project1"): dict[str, str](),
            os.path.join(wd, "project2"): dict[str, str](),
        }
        self.assertDictEqual(res, ans)

    def test_basic1_project1_diff1(self) -> None:
        wd = _get_wd("basic1")
        rules = load_rules(wd)
        diffs = [P1_DIFF1]
        project1_combined_diff = "\n\n".join([file.diff for file in diffs[0].files])
        res = _map_applicable_rules_to_diffs(wd, rules, diffs)
        ans = {
            os.path.join(wd, "project1"): {
                os.path.join(
                    wd,
                    "nazarovkonstantin",
                    "arkcompiler_development_rules",
                    "REVIEW_RULES",
                    "rule1.md",
                ): project1_combined_diff,
                os.path.join(
                    wd,
                    "nazarovkonstantin",
                    "arkcompiler_development_rules",
                    "REVIEW_RULES",
                    "rule3.md",
                ): project1_combined_diff,
                os.path.join(
                    wd,
                    "nazarovkonstantin",
                    "arkcompiler_development_rules",
                    "REVIEW_RULES",
                    "rule4.md",
                ): project1_combined_diff,
            },
        }
        self.assertDictEqual(res, ans)

    def test_basic1_project2_diff2(self) -> None:
        wd = _get_wd("basic1")
        rules = load_rules(wd)
        diffs = [P2_DIFF1]
        project2_combined_diff = "\n\n".join([file.diff for file in diffs[0].files])
        res = _map_applicable_rules_to_diffs(wd, rules, diffs)
        ans = {
            os.path.join(wd, "project2"): {
                os.path.join(
                    wd,
                    "nazarovkonstantin",
                    "arkcompiler_development_rules",
                    "REVIEW_RULES",
                    "rule1.md",
                ): project2_combined_diff,
                os.path.join(
                    wd,
                    "nazarovkonstantin",
                    "arkcompiler_development_rules",
                    "REVIEW_RULES",
                    "rule2.md",
                ): project2_combined_diff,
                os.path.join(
                    wd,
                    "nazarovkonstantin",
                    "arkcompiler_development_rules",
                    "REVIEW_RULES",
                    "rule3.md",
                ): project2_combined_diff,
            },
        }
        self.assertDictEqual(res, ans)

    def test_basic1_project1_diff1_project2_diff2(self) -> None:
        wd = _get_wd("basic1")
        rules = load_rules(wd)
        diffs = [P1_DIFF1, P2_DIFF1]
        project1_combined_diff = "\n\n".join([file.diff for file in diffs[0].files])
        project2_combined_diff = "\n\n".join([file.diff for file in diffs[1].files])
        res = _map_applicable_rules_to_diffs(wd, rules, diffs)
        ans = {
            os.path.join(wd, "project1"): {
                os.path.join(
                    wd,
                    "nazarovkonstantin",
                    "arkcompiler_development_rules",
                    "REVIEW_RULES",
                    "rule1.md",
                ): project1_combined_diff,
                os.path.join(
                    wd,
                    "nazarovkonstantin",
                    "arkcompiler_development_rules",
                    "REVIEW_RULES",
                    "rule4.md",
                ): project1_combined_diff,
                os.path.join(
                    wd,
                    "nazarovkonstantin",
                    "arkcompiler_development_rules",
                    "REVIEW_RULES",
                    "rule3.md",
                ): project1_combined_diff,
            },
            os.path.join(wd, "project2"): {
                os.path.join(
                    wd,
                    "nazarovkonstantin",
                    "arkcompiler_development_rules",
                    "REVIEW_RULES",
                    "rule1.md",
                ): project2_combined_diff,
                os.path.join(
                    wd,
                    "nazarovkonstantin",
                    "arkcompiler_development_rules",
                    "REVIEW_RULES",
                    "rule2.md",
                ): project2_combined_diff,
                os.path.join(
                    wd,
                    "nazarovkonstantin",
                    "arkcompiler_development_rules",
                    "REVIEW_RULES",
                    "rule3.md",
                ): project2_combined_diff,
            },
        }
        self.assertDictEqual(res, ans)


if __name__ == "__main__":
    unittest.main()
