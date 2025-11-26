import unittest
import typing

from app.devagent.stages.review_patches import (
    DevagentViolation,
    DevagentError,
    DevagentReview,
    ReviewPatchResult,
)
from app.devagent.stages.review_wrapup import process_review_result


class ProcessReviewResultTest(unittest.TestCase):
    def test_invalid_review_patch_result(self) -> None:
        with self.assertRaises(AssertionError) as e:
            process_review_result(
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
        res = process_review_result(list())
        res_dict = res.model_dump()
        ans: dict[str, typing.Any] = {"errors": dict(), "results": dict()}
        self.assertDictEqual(ans, res_dict)

        res = process_review_result([list()])
        res_dict = res.model_dump()
        ans = {"errors": dict(), "results": dict()}
        self.assertDictEqual(ans, res_dict)

        res = process_review_result([list(), list(), list()])
        res_dict = res.model_dump()
        ans = {"errors": dict(), "results": dict()}
        self.assertDictEqual(ans, res_dict)

        res = process_review_result(
            [
                list(),
                [
                    ReviewPatchResult(
                        project="project1",
                        error=DevagentError(patch="p", rule="r", message="m"),
                        result=None,
                    )
                ],
                list(),
            ],
        )
        res_dict = res.model_dump()
        ans = {
            "errors": {"project1": [{"message": "m", "patch": "p", "rule": "r"}]},
            "results": dict(),
        }
        self.assertDictEqual(ans, res_dict)

        res = process_review_result(
            [
                list(),
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
                                    rule_url="rc",
                                    message="m",
                                    change_type="ct",
                                    code_snippet="cs",
                                )
                            ]
                        ),
                    )
                ],
                list(),
            ],
        )
        res_dict = res.model_dump()
        ans = {
            "errors": dict(),
            "results": {
                "project1": [
                    {
                        "file": "f",
                        "line": 1,
                        "severity": "s",
                        "rule": "r",
                        "rule_url": "rc",
                        "message": "m",
                        "change_type": "ct",
                        "code_snippet": "cs",
                    }
                ]
            },
        }
        self.assertDictEqual(ans, res_dict)

    def test_basic1(self) -> None:
        res = process_review_result(
            [
                list(),
                [
                    ReviewPatchResult(
                        project="project1",
                        error=DevagentError(patch="p", rule="r", message="m"),
                        result=None,
                    )
                ],
                list(),
            ],
        )
        res_dict = res.model_dump()
        ans: dict[str, typing.Any] = {
            "errors": {"project1": [{"message": "m", "patch": "p", "rule": "r"}]},
            "results": dict(),
        }
        self.assertDictEqual(ans, res_dict)

        res = process_review_result(
            [
                [
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
                                    rule_url="...",
                                    message="msg",
                                    change_type="ct",
                                    code_snippet="cs",
                                )
                            ]
                        ),
                    ),
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
                                    rule_url="...",
                                    message="msg",
                                    change_type="ct",
                                    code_snippet="cs",
                                )
                            ]
                        ),
                    ),
                ],
                [
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
                                    rule_url="...",
                                    message="msg",
                                    change_type="ct",
                                    code_snippet="cs",
                                )
                            ]
                        ),
                    )
                ],
                [
                    ReviewPatchResult(
                        project="project1",
                        error=None,
                        result=DevagentReview(
                            violations=[
                                DevagentViolation(
                                    file="dir2/file",
                                    line=1,
                                    severity="error",
                                    rule="rule4",
                                    rule_url="...",
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
            "errors": dict(),
            "results": {
                "project1": [
                    {
                        "file": "dir1/file",
                        "line": 1,
                        "severity": "error",
                        "rule": "rule1",
                        "rule_url": "...",
                        "message": "msg",
                        "change_type": "ct",
                        "code_snippet": "cs",
                    },
                    {
                        "file": "dir1/file",
                        "line": 1,
                        "severity": "error",
                        "rule": "rule2",
                        "rule_url": "...",
                        "message": "msg",
                        "change_type": "ct",
                        "code_snippet": "cs",
                    },
                    {
                        "file": "file1",
                        "line": 1,
                        "severity": "error",
                        "rule": "rule1",
                        "rule_url": "...",
                        "message": "msg",
                        "change_type": "ct",
                        "code_snippet": "cs",
                    },
                    {
                        "file": "dir2/file",
                        "line": 1,
                        "severity": "error",
                        "rule": "rule4",
                        "rule_url": "...",
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
