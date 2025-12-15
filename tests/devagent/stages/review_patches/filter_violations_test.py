import unittest
import shutil
import os

from app.devagent.stages.review_init import load_rules, prepare_tasks
from app.devagent.stages.review_patches import (
    filter_violations,
    ReviewPatchResult,
    DevagentReview,
    DevagentViolation,
    DevagentError,
)

from tests.devagent.mock.test_diffs.basic1.project1.diff1 import (
    DIFF as P1_DIFF1,
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


def _rule_url(rule_name: str) -> str:
    return f"https://gitcode.com/nazarovkonstantin/arkcompiler_development_rules/tree/main/REVIEW_RULES/{rule_name}.md"


class FilterViolationsTest(unittest.TestCase):
    def test_basic1(self) -> None:
        task_id = f"task_id_{__name__}"
        # diffs = get_diffs(urls)
        diffs = [P2_DIFF1, P1_DIFF1]
        # populate_workdir(wd, diffs)
        wd = _get_wd("basic1")
        rules = load_rules(wd)
        tasks = prepare_tasks(task_id, wd, rules, diffs)
        p1_tasks = {
            os.path.basename(task.rule_path): task
            for task in tasks
            if task.project == "project1"
        }
        p2_tasks = {
            os.path.basename(task.rule_path): task
            for task in tasks
            if task.project == "project2"
        }

        task_p1_rule1 = p1_tasks["rule1.md"]
        task_p1_rule3 = p1_tasks["rule3.md"]
        task_p1_rule4 = p1_tasks["rule4.md"]

        task_p2_rule1 = p2_tasks["rule1.md"]
        task_p2_rule2 = p2_tasks["rule2.md"]
        task_p2_rule3 = p2_tasks["rule3.md"]

        ################
        # empty result #
        ################

        task = task_p1_rule1
        res = ReviewPatchResult(
            project=task.project, error=None, result=DevagentReview(violations=list())
        )
        filtered = filter_violations(res, task)
        self.assertDictEqual(res.model_dump(), filtered.model_dump())

        task = task_p1_rule3
        res = ReviewPatchResult(
            project=task.project, error=None, result=DevagentReview(violations=list())
        )
        filtered = filter_violations(res, task)
        self.assertDictEqual(res.model_dump(), filtered.model_dump())

        task = task_p1_rule4
        res = ReviewPatchResult(
            project=task.project, error=None, result=DevagentReview(violations=list())
        )
        filtered = filter_violations(res, task)
        self.assertDictEqual(res.model_dump(), filtered.model_dump())

        task = task_p2_rule1
        res = ReviewPatchResult(
            project=task.project, error=None, result=DevagentReview(violations=list())
        )
        filtered = filter_violations(res, task)
        self.assertDictEqual(res.model_dump(), filtered.model_dump())

        task = task_p2_rule2
        res = ReviewPatchResult(
            project=task.project, error=None, result=DevagentReview(violations=list())
        )
        filtered = filter_violations(res, task)
        self.assertDictEqual(res.model_dump(), filtered.model_dump())

        task = task_p2_rule3
        res = ReviewPatchResult(
            project=task.project, error=None, result=DevagentReview(violations=list())
        )
        filtered = filter_violations(res, task)
        self.assertDictEqual(res.model_dump(), filtered.model_dump())

        ####################
        # erroneous result #
        ####################

        task = task_p1_rule1
        res = ReviewPatchResult(
            project=task.project,
            error=DevagentError(patch="p", rule="r", message="m"),
            result=None,
        )
        filtered = filter_violations(res, task)
        self.assertDictEqual(res.model_dump(), filtered.model_dump())

        task = task_p1_rule3
        res = ReviewPatchResult(
            project=task.project,
            error=DevagentError(patch="p", rule="r", message="m"),
            result=None,
        )
        filtered = filter_violations(res, task)
        self.assertDictEqual(res.model_dump(), filtered.model_dump())

        task = task_p1_rule4
        res = ReviewPatchResult(
            project=task.project,
            error=DevagentError(patch="p", rule="r", message="m"),
            result=None,
        )
        filtered = filter_violations(res, task)
        self.assertDictEqual(res.model_dump(), filtered.model_dump())

        task = task_p2_rule1
        res = ReviewPatchResult(
            project=task.project,
            error=DevagentError(patch="p", rule="r", message="m"),
            result=None,
        )
        filtered = filter_violations(res, task)
        self.assertDictEqual(res.model_dump(), filtered.model_dump())

        task = task_p2_rule2
        res = ReviewPatchResult(
            project=task.project,
            error=DevagentError(patch="p", rule="r", message="m"),
            result=None,
        )
        filtered = filter_violations(res, task)
        self.assertDictEqual(res.model_dump(), filtered.model_dump())

        task = task_p2_rule3
        res = ReviewPatchResult(
            project=task.project,
            error=DevagentError(patch="p", rule="r", message="m"),
            result=None,
        )
        filtered = filter_violations(res, task)
        self.assertDictEqual(res.model_dump(), filtered.model_dump())

        ####################
        # valid violations #
        ####################

        task = task_p1_rule1
        res = ReviewPatchResult(
            project=task.project,
            error=None,
            result=DevagentReview(
                violations=[
                    DevagentViolation(
                        file="dir1/file1",
                        line=1,
                        severity="s",
                        rule="rule1",
                        rule_url=_rule_url("rule1"),
                        message="m",
                        change_type="ct",
                        code_snippet="cs",
                    )
                ],
            ),
        )
        filtered = filter_violations(res, task)
        self.assertDictEqual(res.model_dump(), filtered.model_dump())

        task = task_p1_rule3
        res = ReviewPatchResult(
            project=task.project,
            error=None,
            result=DevagentReview(
                violations=[
                    DevagentViolation(
                        file="dir2/file1",
                        line=1,
                        severity="s",
                        rule="rule3",
                        rule_url=_rule_url("rule3"),
                        message="m",
                        change_type="ct",
                        code_snippet="cs",
                    )
                ],
            ),
        )
        filtered = filter_violations(res, task)
        self.assertDictEqual(res.model_dump(), filtered.model_dump())

        task = task_p1_rule4
        res = ReviewPatchResult(
            project=task.project,
            error=None,
            result=DevagentReview(
                violations=[
                    DevagentViolation(
                        file="dir2/file1",
                        line=1,
                        severity="s",
                        rule="rule4",
                        rule_url=_rule_url("rule4"),
                        message="m",
                        change_type="ct",
                        code_snippet="cs",
                    )
                ],
            ),
        )
        filtered = filter_violations(res, task)
        self.assertDictEqual(res.model_dump(), filtered.model_dump())

        task = task_p2_rule1
        res = ReviewPatchResult(
            project=task.project,
            error=None,
            result=DevagentReview(
                violations=[
                    DevagentViolation(
                        file="dir1/file1",
                        line=1,
                        severity="s",
                        rule="rule1",
                        rule_url=_rule_url("rule1"),
                        message="m",
                        change_type="ct",
                        code_snippet="cs",
                    )
                ],
            ),
        )
        filtered = filter_violations(res, task)
        self.assertDictEqual(res.model_dump(), filtered.model_dump())

        task = task_p2_rule2
        res = ReviewPatchResult(
            project=task.project,
            error=None,
            result=DevagentReview(
                violations=[
                    DevagentViolation(
                        file="new_file",
                        line=1,
                        severity="s",
                        rule="rule2",
                        rule_url=_rule_url("rule2"),
                        message="m",
                        change_type="ct",
                        code_snippet="cs",
                    ),
                    DevagentViolation(
                        file="new_dir/new_file",
                        line=1,
                        severity="s",
                        rule="rule2",
                        rule_url=_rule_url("rule2"),
                        message="m",
                        change_type="ct",
                        code_snippet="cs",
                    ),
                    DevagentViolation(
                        file="dir1/file1",
                        line=1,
                        severity="s",
                        rule="rule2",
                        rule_url=_rule_url("rule2"),
                        message="m",
                        change_type="ct",
                        code_snippet="cs",
                    ),
                ],
            ),
        )
        filtered = filter_violations(res, task)
        self.assertDictEqual(res.model_dump(), filtered.model_dump())

        task = task_p2_rule3
        res = ReviewPatchResult(
            project=task.project,
            error=None,
            result=DevagentReview(
                violations=[
                    DevagentViolation(
                        file="dir3/file1",
                        line=1,
                        severity="s",
                        rule="rule3",
                        rule_url=_rule_url("rule3"),
                        message="m",
                        change_type="ct",
                        code_snippet="cs",
                    )
                ],
            ),
        )
        filtered = filter_violations(res, task)
        self.assertDictEqual(res.model_dump(), filtered.model_dump())

        #############################
        # invalid rule filtered out #
        #############################

        task = task_p1_rule1
        res = ReviewPatchResult(
            project=task.project,
            error=None,
            result=DevagentReview(
                violations=[
                    DevagentViolation(
                        file="dir1/file1",
                        line=1,
                        severity="s",
                        rule="rule4",
                        rule_url=_rule_url("rule4"),
                        message="m",
                        change_type="ct",
                        code_snippet="cs",
                    ),
                    DevagentViolation(
                        file="dir1/file1",
                        line=1,
                        severity="s",
                        rule="rule2",
                        rule_url=_rule_url("rule2"),
                        message="m",
                        change_type="ct",
                        code_snippet="cs",
                    ),
                ],
            ),
        )
        filtered = filter_violations(res, task)
        self.assertDictEqual(
            ReviewPatchResult(
                project=task.project,
                error=None,
                result=DevagentReview(violations=list()),
            ).model_dump(),
            filtered.model_dump(),
        )

        task = task_p1_rule3
        res = ReviewPatchResult(
            project=task.project,
            error=None,
            result=DevagentReview(
                violations=[
                    DevagentViolation(
                        file="dir2/file1",
                        line=1,
                        severity="s",
                        rule="rule4",
                        rule_url=_rule_url("rule4"),
                        message="m",
                        change_type="ct",
                        code_snippet="cs",
                    ),
                    DevagentViolation(
                        file="dir2/file1",
                        line=1,
                        severity="s",
                        rule="rule1",
                        rule_url=_rule_url("rule1"),
                        message="m",
                        change_type="ct",
                        code_snippet="cs",
                    ),
                ],
            ),
        )
        filtered = filter_violations(res, task)
        self.assertDictEqual(
            ReviewPatchResult(
                project=task.project,
                error=None,
                result=DevagentReview(violations=list()),
            ).model_dump(),
            filtered.model_dump(),
        )

        task = task_p1_rule4
        res = ReviewPatchResult(
            project=task.project,
            error=None,
            result=DevagentReview(
                violations=[
                    DevagentViolation(
                        file="dir2/file1",
                        line=1,
                        severity="s",
                        rule="rule3",
                        rule_url=_rule_url("rule3"),
                        message="m",
                        change_type="ct",
                        code_snippet="cs",
                    ),
                    DevagentViolation(
                        file="dir2/file1",
                        line=1,
                        severity="s",
                        rule="rule1",
                        rule_url=_rule_url("rule1"),
                        message="m",
                        change_type="ct",
                        code_snippet="cs",
                    ),
                ],
            ),
        )
        filtered = filter_violations(res, task)
        self.assertDictEqual(
            ReviewPatchResult(
                project=task.project,
                error=None,
                result=DevagentReview(violations=list()),
            ).model_dump(),
            filtered.model_dump(),
        )

        task = task_p2_rule1
        res = ReviewPatchResult(
            project=task.project,
            error=None,
            result=DevagentReview(
                violations=[
                    DevagentViolation(
                        file="dir1/file1",
                        line=1,
                        severity="s",
                        rule="rule4",
                        rule_url=_rule_url("rule4"),
                        message="m",
                        change_type="ct",
                        code_snippet="cs",
                    ),
                    DevagentViolation(
                        file="dir1/file1",
                        line=1,
                        severity="s",
                        rule="rule2",
                        rule_url=_rule_url("rule2"),
                        message="m",
                        change_type="ct",
                        code_snippet="cs",
                    ),
                ],
            ),
        )
        filtered = filter_violations(res, task)
        self.assertDictEqual(
            ReviewPatchResult(
                project=task.project,
                error=None,
                result=DevagentReview(violations=list()),
            ).model_dump(),
            filtered.model_dump(),
        )

        task = task_p2_rule2
        res = ReviewPatchResult(
            project=task.project,
            error=None,
            result=DevagentReview(
                violations=[
                    DevagentViolation(
                        file="new_file",
                        line=1,
                        severity="s",
                        rule="rule4",
                        rule_url=_rule_url("rule4"),
                        message="m",
                        change_type="ct",
                        code_snippet="cs",
                    ),
                    DevagentViolation(
                        file="new_file2",
                        line=1,
                        severity="s",
                        rule="rule1",
                        rule_url=_rule_url("rule1"),
                        message="m",
                        change_type="ct",
                        code_snippet="cs",
                    ),
                ],
            ),
        )
        filtered = filter_violations(res, task)
        self.assertDictEqual(
            ReviewPatchResult(
                project=task.project,
                error=None,
                result=DevagentReview(violations=list()),
            ).model_dump(),
            filtered.model_dump(),
        )

        task = task_p2_rule3
        res = ReviewPatchResult(
            project=task.project,
            error=None,
            result=DevagentReview(
                violations=[
                    DevagentViolation(
                        file="dir3/file1",
                        line=1,
                        severity="s",
                        rule="rule4",
                        rule_url=_rule_url("rule4"),
                        message="m",
                        change_type="ct",
                        code_snippet="cs",
                    ),
                    DevagentViolation(
                        file="dir3/file1",
                        line=1,
                        severity="s",
                        rule="rule1",
                        rule_url=_rule_url("rule1"),
                        message="m",
                        change_type="ct",
                        code_snippet="cs",
                    ),
                ],
            ),
        )
        filtered = filter_violations(res, task)
        self.assertDictEqual(
            ReviewPatchResult(
                project=task.project,
                error=None,
                result=DevagentReview(violations=list()),
            ).model_dump(),
            filtered.model_dump(),
        )

        ############################
        # invalid dir filtered out #
        ############################

        task = task_p1_rule1
        res = ReviewPatchResult(
            project=task.project,
            error=None,
            result=DevagentReview(
                violations=[
                    DevagentViolation(
                        file="dir1/file1",
                        line=1,
                        severity="s",
                        rule="rule1",
                        rule_url=_rule_url("rule1"),
                        message="m",
                        change_type="ct",
                        code_snippet="cs",
                    ),
                    DevagentViolation(
                        file="new_dir/file1",
                        line=1,
                        severity="s",
                        rule="rule1",
                        rule_url=_rule_url("rule1"),
                        message="m",
                        change_type="ct",
                        code_snippet="cs",
                    ),
                ],
            ),
        )
        filtered = filter_violations(res, task)
        self.assertDictEqual(
            ReviewPatchResult(
                project=task.project,
                error=None,
                result=DevagentReview(
                    violations=[
                        DevagentViolation(
                            file="dir1/file1",
                            line=1,
                            severity="s",
                            rule="rule1",
                            rule_url=_rule_url("rule1"),
                            message="m",
                            change_type="ct",
                            code_snippet="cs",
                        )
                    ],
                ),
            ).model_dump(),
            filtered.model_dump(),
        )

        task = task_p1_rule3
        res = ReviewPatchResult(
            project=task.project,
            error=None,
            result=DevagentReview(
                violations=[
                    DevagentViolation(
                        file="dir2/file1",
                        line=1,
                        severity="s",
                        rule="rule3",
                        rule_url=_rule_url("rule3"),
                        message="m",
                        change_type="ct",
                        code_snippet="cs",
                    ),
                    DevagentViolation(
                        file="file1",
                        line=1,
                        severity="s",
                        rule="rule3",
                        rule_url=_rule_url("rule3"),
                        message="m",
                        change_type="ct",
                        code_snippet="cs",
                    ),
                ],
            ),
        )
        filtered = filter_violations(res, task)
        self.assertDictEqual(
            ReviewPatchResult(
                project=task.project,
                error=None,
                result=DevagentReview(
                    violations=[
                        DevagentViolation(
                            file="dir2/file1",
                            line=1,
                            severity="s",
                            rule="rule3",
                            rule_url=_rule_url("rule3"),
                            message="m",
                            change_type="ct",
                            code_snippet="cs",
                        )
                    ],
                ),
            ).model_dump(),
            filtered.model_dump(),
        )

        task = task_p1_rule4
        res = ReviewPatchResult(
            project=task.project,
            error=None,
            result=DevagentReview(
                violations=[
                    DevagentViolation(
                        file="dir2/file1",
                        line=1,
                        severity="s",
                        rule="rule4",
                        rule_url=_rule_url("rule4"),
                        message="m",
                        change_type="ct",
                        code_snippet="cs",
                    ),
                    DevagentViolation(
                        file="dir3/file1",
                        line=1,
                        severity="s",
                        rule="rule4",
                        rule_url=_rule_url("rule4"),
                        message="m",
                        change_type="ct",
                        code_snippet="cs",
                    ),
                ],
            ),
        )
        filtered = filter_violations(res, task)
        self.assertDictEqual(
            ReviewPatchResult(
                project=task.project,
                error=None,
                result=DevagentReview(
                    violations=[
                        DevagentViolation(
                            file="dir2/file1",
                            line=1,
                            severity="s",
                            rule="rule4",
                            rule_url=_rule_url("rule4"),
                            message="m",
                            change_type="ct",
                            code_snippet="cs",
                        )
                    ],
                ),
            ).model_dump(),
            filtered.model_dump(),
        )

        task = task_p2_rule1
        res = ReviewPatchResult(
            project=task.project,
            error=None,
            result=DevagentReview(
                violations=[
                    DevagentViolation(
                        file="dir1/file1",
                        line=1,
                        severity="s",
                        rule="rule1",
                        rule_url=_rule_url("rule1"),
                        message="m",
                        change_type="ct",
                        code_snippet="cs",
                    ),
                    DevagentViolation(
                        file="dir2/file1",
                        line=1,
                        severity="s",
                        rule="rule1",
                        rule_url=_rule_url("rule1"),
                        message="m",
                        change_type="ct",
                        code_snippet="cs",
                    ),
                ],
            ),
        )
        filtered = filter_violations(res, task)
        self.assertDictEqual(
            ReviewPatchResult(
                project=task.project,
                error=None,
                result=DevagentReview(
                    violations=[
                        DevagentViolation(
                            file="dir1/file1",
                            line=1,
                            severity="s",
                            rule="rule1",
                            rule_url=_rule_url("rule1"),
                            message="m",
                            change_type="ct",
                            code_snippet="cs",
                        )
                    ],
                ),
            ).model_dump(),
            filtered.model_dump(),
        )

        task = task_p2_rule2
        res = ReviewPatchResult(
            project=task.project,
            error=None,
            result=DevagentReview(
                violations=[
                    DevagentViolation(
                        file="new_file",
                        line=1,
                        severity="s",
                        rule="rule2",
                        rule_url=_rule_url("rule2"),
                        message="m",
                        change_type="ct",
                        code_snippet="cs",
                    )
                ],
            ),
        )
        filtered = filter_violations(res, task)
        self.assertDictEqual(
            ReviewPatchResult(
                project=task.project,
                error=None,
                result=DevagentReview(
                    violations=[
                        DevagentViolation(
                            file="new_file",
                            line=1,
                            severity="s",
                            rule="rule2",
                            rule_url=_rule_url("rule2"),
                            message="m",
                            change_type="ct",
                            code_snippet="cs",
                        ),
                    ],
                ),
            ).model_dump(),
            filtered.model_dump(),
        )

        task = task_p2_rule3
        res = ReviewPatchResult(
            project=task.project,
            error=None,
            result=DevagentReview(
                violations=[
                    DevagentViolation(
                        file="dir3/file1",
                        line=1,
                        severity="s",
                        rule="rule3",
                        rule_url=_rule_url("rule3"),
                        message="m",
                        change_type="ct",
                        code_snippet="cs",
                    ),
                    DevagentViolation(
                        file="dir1/file1",
                        line=1,
                        severity="s",
                        rule="rule3",
                        rule_url=_rule_url("rule3"),
                        message="m",
                        change_type="ct",
                        code_snippet="cs",
                    ),
                    DevagentViolation(
                        file="dir3/dir/file",
                        line=1,
                        severity="s",
                        rule="rule3",
                        rule_url=_rule_url("rule3"),
                        message="m",
                        change_type="ct",
                        code_snippet="cs",
                    ),
                    DevagentViolation(
                        file="dir3/dir_file",
                        line=1,
                        severity="s",
                        rule="rule3",
                        rule_url=_rule_url("rule3"),
                        message="m",
                        change_type="ct",
                        code_snippet="cs",
                    ),
                ],
            ),
        )
        filtered = filter_violations(res, task)
        self.assertDictEqual(
            ReviewPatchResult(
                project=task.project,
                error=None,
                result=DevagentReview(
                    violations=[
                        DevagentViolation(
                            file="dir3/file1",
                            line=1,
                            severity="s",
                            rule="rule3",
                            rule_url=_rule_url("rule3"),
                            message="m",
                            change_type="ct",
                            code_snippet="cs",
                        ),
                        DevagentViolation(
                            file="dir3/dir_file",
                            line=1,
                            severity="s",
                            rule="rule3",
                            rule_url=_rule_url("rule3"),
                            message="m",
                            change_type="ct",
                            code_snippet="cs",
                        ),
                    ],
                ),
            ).model_dump(),
            filtered.model_dump(),
        )

        _clean_wd(wd)


if __name__ == "__main__":
    unittest.main()
