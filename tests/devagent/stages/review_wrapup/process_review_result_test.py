import unittest
import typing
import os


from app.devagent.stages.review_init import load_rules
from app.devagent.stages.review_patches import (
    DevagentViolation,
    DevagentError,
    DevagentReview,
    ReviewPatchResult,
)
from app.devagent.stages.review_wrapup import process_review_result, ProcessedReview


def _get_wd(wd_name: str) -> str:
    cur_dir = os.path.dirname(os.path.realpath(__file__))
    wd = os.path.normpath(
        os.path.join(cur_dir, "..", "..", "mock", "test_workdirs", wd_name)
    )
    return wd


class ProcessReviewResultTest(unittest.TestCase):
    def test_invalid_review_patch_result(self) -> None:
        wd = _get_wd("basic")
        rules = load_rules(wd)

        with self.assertRaises(AssertionError) as e:
            process_review_result(
                rules,
                [
                    [
                        ReviewPatchResult(
                            project="project1",
                            error=None,
                            result=None,
                        )
                    ]
                ],
            )

        self.assertTrue(
            "`error` and `result` are mutually exclusive and can not be both None"
            in str(e.exception)
        )

    def test_basic(self) -> None:
        wd = _get_wd("basic")
        rules = load_rules(wd)

        res = process_review_result(rules, [])
        res_dict = res.model_dump()
        ans: dict[str, typing.Any] = {"errors": {}, "results": {}}
        self.assertDictEqual(ans, res_dict)

        res = process_review_result(rules, [[]])
        res_dict = res.model_dump()
        ans = {"errors": {}, "results": {}}
        self.assertDictEqual(ans, res_dict)

        res = process_review_result(rules, [[], [], []])
        res_dict = res.model_dump()
        ans = {"errors": {}, "results": {}}
        self.assertDictEqual(ans, res_dict)

        res = process_review_result(
            rules,
            [
                [],
                [
                    ReviewPatchResult(
                        project="project1",
                        error=DevagentError(patch="p", rule="r", message="m"),
                        result=None,
                    )
                ],
                [],
            ],
        )
        res_dict = res.model_dump()
        ans = {
            "errors": {"project1": [{"message": "m", "patch": "p", "rule": "r"}]},
            "results": {},
        }
        self.assertDictEqual(ans, res_dict)

        res = process_review_result(
            rules,
            [
                [],
                [
                    ReviewPatchResult(
                        project="project1",
                        error=None,
                        result=DevagentReview(
                            violations=[
                                DevagentViolation(
                                    file="f",
                                    line=1,
                                    severity="s",
                                    rule="r",
                                    message="m",
                                    change_type="ct",
                                    code_snippet="cs",
                                )
                            ]
                        ),
                    )
                ],
                [],
            ],
        )
        res_dict = res.model_dump()
        ans = {
            "errors": {},
            "results": {"project1": []},
        }
        self.assertDictEqual(ans, res_dict)

    def test_basic1(self) -> None:
        wd = _get_wd("basic1")
        rules = load_rules(wd)

        res = process_review_result(
            rules,
            [
                [],
                [
                    ReviewPatchResult(
                        project="project1",
                        error=DevagentError(patch="p", rule="r", message="m"),
                        result=None,
                    )
                ],
                [],
            ],
        )
        res_dict = res.model_dump()
        ans: dict[str, typing.Any] = {
            "errors": {"project1": [{"message": "m", "patch": "p", "rule": "r"}]},
            "results": {},
        }
        self.assertDictEqual(ans, res_dict)

        res = process_review_result(
            rules,
            [
                [
                    # keep
                    ReviewPatchResult(
                        project="project1",
                        error=None,
                        result=DevagentReview(
                            violations=[
                                DevagentViolation(
                                    file="dir1/file",
                                    line=1,
                                    severity="error",
                                    rule="rule1",
                                    message="msg",
                                    change_type="ct",
                                    code_snippet="cs",
                                )
                            ]
                        ),
                    ),
                    # discard, rule does not apply
                    ReviewPatchResult(
                        project="project1",
                        error=None,
                        result=DevagentReview(
                            violations=[
                                DevagentViolation(
                                    file="dir1/file",
                                    line=1,
                                    severity="error",
                                    rule="rule2",
                                    message="msg",
                                    change_type="ct",
                                    code_snippet="cs",
                                )
                            ]
                        ),
                    ),
                ],
                [
                    # discard, rule does not apply
                    ReviewPatchResult(
                        project="project1",
                        error=None,
                        result=DevagentReview(
                            violations=[
                                DevagentViolation(
                                    file="file1",
                                    line=1,
                                    severity="error",
                                    rule="rule1",
                                    message="msg",
                                    change_type="ct",
                                    code_snippet="cs",
                                )
                            ]
                        ),
                    )
                ],
                [
                    # keep
                    ReviewPatchResult(
                        project="project1",
                        error=None,
                        result=DevagentReview(
                            violations=[
                                DevagentViolation(
                                    file="dir2/file",
                                    line=1,
                                    severity="error",
                                    rule="rule2",
                                    message="msg",
                                    change_type="ct",
                                    code_snippet="cs",
                                )
                            ]
                        ),
                    ),
                ],
            ],
        )
        res_dict = res.model_dump()
        ans = {
            "errors": {},
            "results": {
                "project1": [
                    {
                        "file": "dir1/file",
                        "line": 1,
                        "severity": "error",
                        "rule": "rule1",
                        "message": "msg",
                        "change_type": "ct",
                        "code_snippet": "cs",
                    },
                    {
                        "file": "dir2/file",
                        "line": 1,
                        "severity": "error",
                        "rule": "rule2",
                        "message": "msg",
                        "change_type": "ct",
                        "code_snippet": "cs",
                    },
                ]
            },
        }
        self.assertDictEqual(ans, res_dict)


if __name__ == "__main__":
    unittest.main()
