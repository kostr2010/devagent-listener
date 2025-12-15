import re
from dataclasses import dataclass
from typing import Literal


@dataclass
class FileInfo:
    old_name: str = ""
    new_name: str = ""
    num_added_lines: int = 0
    num_removed_lines: int = 0
    num_added_assertions: int = 0
    num_removed_assertions: int = 0
    num_context_assertions: int = 0
    num_added_cte_checks: int = 0
    num_removed_cte_checks: int = 0
    num_context_cte_checks: int = 0

    state: Literal["modified", "added", "removed", "renamed"] = "modified"

    type: Literal[
        "other",
        "runtime",
        "runtime ETS stdlib",
        "front-end",
        "front-end parser",
        "front-end checker",
        "front-end AST verifier",
        "front-end code generator",
        "test",
        "unit test",
        "front-end test",
        "negative front-end test",
        "positive front-end test",
        "CTS test",
        "positive CTS test",
        "negative CTS test",
        "functional test",
        "negative functional test",
        "positive functional test",
    ] = "other"

    @staticmethod
    def _is_cpp_file(s: str) -> bool:
        return s.endswith(".cpp") or s.endswith(".h")

    @staticmethod
    def _is_ets_file(s: str) -> bool:
        return s.endswith(".ets") or s.endswith(".sts")

    def _assertParsed(self) -> None:
        assert len(self.old_name) > 0
        assert len(self.new_name) > 0
        assert self.num_added_lines >= 0
        assert self.num_removed_lines >= 0
        assert self.num_added_assertions >= 0
        assert self.num_removed_assertions >= 0
        assert self.num_context_assertions >= 0
        assert self.num_added_cte_checks >= 0
        assert self.num_removed_cte_checks >= 0
        assert self.num_context_cte_checks >= 0
        # These will be inferred further, must not be touched during parsing:
        assert self.state == "modified"
        assert self.type == "other"

    def _inferState(self) -> None:
        DEV_NULL: str = "/dev/null"

        if self.old_name == DEV_NULL:
            assert self.new_name != DEV_NULL
            assert self.num_removed_lines == 0
            self.state = "added"

        if self.new_name == DEV_NULL:
            assert self.old_name != DEV_NULL
            assert self.num_added_lines == 0
            self.state = "removed"

        if self.state == "modified" and self.old_name != self.new_name:
            if self.num_added_lines == 0 and self.num_removed_lines == 0:
                self.state = "renamed"

    def _inferFileType(self) -> None:
        assert self.type == "other"

        path = self.new_name
        if "/test" in path:
            self.type = "test"

            if FileInfo._is_cpp_file(path):
                self.type = "unit test"
            elif FileInfo._is_ets_file(path):
                if "ets2panda/test" in path:
                    self.type = "front-end test"
                    if "ets2panda/test/ast" in path:
                        self.type = "negative front-end test"
                    elif "ets2panda/test/runtime" in path:
                        self.type = "positive front-end test"
                elif "tests/ets-templates" in path:
                    self.type = "CTS test"
                    # TODO(igelhaus): inference for positive / negative cases
                elif "ets_func_tests" in path:
                    self.type = "functional test"
                    # TODO(igelhaus): inference for positive / negative cases

        elif "ets2panda/" in path:
            self.type = "front-end"

            if FileInfo._is_cpp_file(path):
                if "ets2panda/parser/" in path or "ets2panda/ir/" in path:
                    self.type = "front-end parser"
                elif "ets2panda/checker/" in path:
                    self.type = "front-end checker"
                elif "ets2panda/ast_verifier" in path:
                    self.type = "front-end AST verifier"
                elif "ETSGen." in path or "ETSemitter." in path:
                    self.type = "front-end code generator"

        elif "static_core/" in path:
            if "stdlib/" in path:
                self.type = "runtime ETS stdlib"
            elif FileInfo._is_cpp_file(path):
                self.type = "runtime"

    def enrich(self) -> None:
        self._assertParsed()
        self._inferState()
        self._inferFileType()

    def removesAssertions(self) -> bool:
        return self.num_removed_assertions > self.num_added_assertions

    def addsAssertions(self) -> bool:
        return self.num_added_assertions > self.num_removed_assertions


class PatchAnalyzer:
    """Parse unified diff patches into structured project-specific data."""

    OLD_FILE_HEADER = re.compile(r"^--- (?:a/)?(.+)$")
    NEW_FILE_HEADER = re.compile(r"^\+\+\+ (?:b/)?(.+)$")

    @staticmethod
    def _contains_any_assertion(s: str) -> bool:
        """Heuristic: Determines if a string s contains an assertion."""

        return "ES2PANDA_ASSERT(" in s or "arktest.assert" in s or "ASSERT(" in s

    @staticmethod
    def _contains_cte_check(s: str) -> bool:
        """Heuristic: Determines if a string s contains a CTE check marker."""

        return "/* @@" in s

    def __init__(self, patch_name: str) -> None:
        """Initialize the analyzer with the patch.

        Args:
            patch_name: Path to the patch file in the unified diff format
        """

        self.patch_name = patch_name
        self.file_facts = list[FileInfo]()

    def _commit_file_info(self, fi: FileInfo | None) -> None:
        """Appends a new FileInfo item fi to the internal storage."""

        if fi is None:
            return
        fi.enrich()
        self.file_facts.append(fi)

    def analyze(self) -> bool:
        """Reads the patch creating a FileInfo item per each parsed file."""

        self.file_facts.clear()

        try:
            with open(self.patch_name, "r") as patch:
                curr_file: FileInfo | None = None

                for line in patch:
                    if match := self.OLD_FILE_HEADER.match(line):
                        self._commit_file_info(curr_file)

                        curr_file = FileInfo()
                        curr_file.old_name = match.group(1)

                    elif match := self.NEW_FILE_HEADER.match(line):
                        assert curr_file is not None
                        curr_file.new_name = match.group(1)

                    elif line.startswith("@@"):
                        assert curr_file is not None

                    elif line.startswith("+"):
                        assert curr_file is not None
                        curr_file.num_added_lines += 1
                        if PatchAnalyzer._contains_any_assertion(line):
                            curr_file.num_added_assertions += 1
                        if PatchAnalyzer._contains_cte_check(line):
                            curr_file.num_added_cte_checks += 1

                    elif line.startswith("-"):
                        assert curr_file is not None
                        curr_file.num_removed_lines += 1
                        if PatchAnalyzer._contains_any_assertion(line):
                            curr_file.num_removed_assertions += 1
                        if PatchAnalyzer._contains_cte_check(line):
                            curr_file.num_removed_cte_checks += 1

                    elif line.startswith(" "):
                        assert curr_file is not None
                        if PatchAnalyzer._contains_any_assertion(line):
                            curr_file.num_context_assertions += 1
                        if PatchAnalyzer._contains_cte_check(line):
                            curr_file.num_context_cte_checks += 1

                    else:
                        pass

                assert curr_file is not None
                self._commit_file_info(curr_file)
        except FileNotFoundError:
            print(f"Error: The file '{self.patch_name}' was not found.")
            return False
        except Exception as e:
            print(f"An error occurred: {e}")
            return False

        return True

    def _countFrontendContribs(self) -> tuple[int, int]:
        """Private: Yet another contrib counter."""

        num_added: int = 0
        num_removed: int = 0
        for fi in self.file_facts:
            if "front-end" in fi.type and not "test" in fi.type:
                num_added += fi.num_added_lines
                num_removed += fi.num_removed_lines
        return (num_added, num_removed)

    def _countRuntimeContribs(self) -> tuple[int, int]:
        """Private: Yet another contrib counter."""

        num_added: int = 0
        num_removed: int = 0
        for fi in self.file_facts:
            if "runtime" in fi.type and not "test" in fi.type:
                num_added += fi.num_added_lines
                num_removed += fi.num_removed_lines
        return (num_added, num_removed)

    def _countETSStdlibContribs(self) -> tuple[int, int]:
        """Private: Yet another contrib counter."""

        num_added: int = 0
        num_removed: int = 0
        for fi in self.file_facts:
            if fi.type == "runtime ETS stdlib":
                num_added += fi.num_added_lines
                num_removed += fi.num_removed_lines
        return (num_added, num_removed)

    def _countParserContribs(self) -> tuple[int, int]:
        """Private: Yet another contrib counter."""

        num_added: int = 0
        num_removed: int = 0
        for fi in self.file_facts:
            if fi.type == "front-end parser":
                num_added += fi.num_added_lines
                num_removed += fi.num_removed_lines
        return (num_added, num_removed)

    def _countCheckerContribs(self) -> tuple[int, int]:
        """Private: Yet another contrib counter."""

        num_added: int = 0
        num_removed: int = 0
        for fi in self.file_facts:
            if fi.type == "front-end checker":
                num_added += fi.num_added_lines
                num_removed += fi.num_removed_lines

        return (num_added, num_removed)

    def _countASTVerifierContribs(self) -> tuple[int, int]:
        """Private: Yet another contrib counter."""

        num_added: int = 0
        num_removed: int = 0
        for fi in self.file_facts:
            if fi.type == "front-end AST verifier":
                num_added += fi.num_added_lines
                num_removed += fi.num_removed_lines
        return (num_added, num_removed)

    def _countCodegenContribs(self) -> tuple[int, int]:
        """Private: Yet another contrib counter."""

        num_added: int = 0
        num_removed: int = 0
        for fi in self.file_facts:
            if fi.type == "front-end code generator":
                num_added += fi.num_added_lines
                num_removed += fi.num_removed_lines
        return (num_added, num_removed)

    def _countTestContribs(self) -> tuple[int, int]:
        """Private: Yet another contrib counter."""

        num_added: int = 0
        num_removed: int = 0
        for fi in self.file_facts:
            if "test" in fi.type:
                num_added += fi.num_added_lines
                num_removed += fi.num_removed_lines
        return (num_added, num_removed)

    def _countAddedTests(self) -> int:
        """Private: Yet another file counter."""

        n: int = 0
        for fi in self.file_facts:
            if "test" in fi.type and fi.state == "added":
                n += 1
        return n

    def _countRemovedTests(self) -> int:
        """Private: Yet another file counter."""

        n: int = 0
        for fi in self.file_facts:
            if "test" in fi.type and fi.state == "removed":
                n += 1
        return n

    def _countModifiedTests(self) -> int:
        """Private: Yet another file counter."""

        n: int = 0
        for fi in self.file_facts:
            if "test" in fi.type and fi.state == "modified":
                n += 1
        return n

    def _countPositiveTestsWithoutAssertions(self) -> int:
        """Private: Yet another file counter."""

        n: int = 0

        for fi in self.file_facts:
            if not "test" in fi.type:
                continue
            if not "positive" in fi.type:
                continue

            if fi.state == "added" and fi.num_added_assertions == 0:
                n += 1

            if fi.state == "removed" and fi.num_removed_assertions > 0:
                n += 1

            if fi.state == "modified" and fi.removesAssertions():
                n += 1

        return n

    def verboseFrontEndSummary(self) -> str:
        """Based on the patch, summarizes front-end contribution
        informartion into a human-readable string.
        """

        fe_contribs = self._countFrontendContribs()

        if fe_contribs[0] + fe_contribs[1] == 0:
            return "This patch does not contribute to the front-end.\n\n"

        summary = "This patch contributes to the front-end main code base.\n\n"
        summary += f"Overall, {fe_contribs[0]} LoC "
        summary += "are added, and "
        summary += f"{fe_contribs[1]} LoC "
        summary += "are removed"
        summary += ".\n\n"

        parser_contribs = self._countParserContribs()
        if parser_contribs[0] + parser_contribs[1]:
            summary += f"In particular, {parser_contribs[0]} LoC "
            summary += "are added to the parser, "
            summary += f"{parser_contribs[1]} LoC "
            summary += "are removed from the parser"
            summary += ".\n\n"

        checker_contribs = self._countCheckerContribs()
        if checker_contribs[0] + checker_contribs[1]:
            summary += f"In particular, {checker_contribs[0]} LoC "
            summary += "are added to the type checker, "
            summary += f"{checker_contribs[1]} LoC "
            summary += "are removed from the type checker"
            summary += ".\n\n"

        astverifier_contribs = self._countASTVerifierContribs()
        if astverifier_contribs[0] + astverifier_contribs[1]:
            summary += f"In particular, {astverifier_contribs[0]} LoC "
            summary += "are added to the AST verifier, "
            summary += f"{astverifier_contribs[1]} LoC "
            summary += "are removed from the AST verifier"
            summary += ".\n\n"

        codegen_contribs = self._countCodegenContribs()
        if codegen_contribs[0] + codegen_contribs[1]:
            summary += f"In particular, {codegen_contribs[0]} LoC "
            summary += "are added to the code generator, "
            summary += f"{codegen_contribs[1]} LoC "
            summary += "are removed from the code generator"
            summary += ".\n\n"

        return summary

    def verboseTestSummary(self) -> str:
        """Based on the patch, summarizes test contribution
        informartion into a human-readable string.
        """

        num_added_tests = self._countAddedTests()
        num_removed_tests = self._countRemovedTests()
        num_modified_tests = self._countModifiedTests()

        if num_added_tests + num_removed_tests + num_modified_tests == 0:
            return "The patch does not contribute to the tests.\n\n"

        summary = "This patch contributes to the tests.\n\n"

        test_contribs = self._countTestContribs()
        summary += f"Overall, {test_contribs[0]} LoC "
        summary += "are added to the tests, and "
        summary += f"{test_contribs[1]} LoC "
        summary += "are removed from the tests"
        summary += ".\n\n"

        summary += "In particular, the patch "
        summary += (
            f"adds {num_added_tests} tests"
            if num_added_tests > 0
            else "does not add tests"
        )
        summary += ", "
        summary += (
            f"removes {num_removed_tests} tests"
            if num_removed_tests > 0
            else "does not remove tests"
        )
        summary += ", "
        summary += (
            f"modifies {num_modified_tests} existing tests"
            if num_modified_tests > 0
            else "does not modify existing tests"
        )
        summary += ".\n\n"

        num_without_assertions = self._countPositiveTestsWithoutAssertions()
        if num_without_assertions > 0:
            summary += f"The patch has {num_without_assertions} "
            summary += "positive tests which decrease assertion usage"
            summary += ".\n\n"

        return summary

    def verboseRuntimeSummary(self) -> str:
        summary = ""
        """Based on the patch, summarizes runtime contribution
        informartion into a human-readable string.
        """

        rt_contribs = self._countRuntimeContribs()

        if rt_contribs[0] + rt_contribs[1] == 0:
            return "This patch does not contribute to the runtime.\n\n"

        summary = "This patch contributes to the runtime main code base.\n\n"
        summary += f"Overall, {rt_contribs[0]} LoC "
        summary += "are added, and "
        summary += f"{rt_contribs[1]} LoC "
        summary += "are removed"
        summary += ".\n\n"

        stdlib_contribs = self._countETSStdlibContribs()
        if stdlib_contribs[0] + stdlib_contribs[1]:
            summary += f"In particular, {stdlib_contribs[0]} LoC "
            summary += "are added to the ETS stdlib, "
            summary += f"{stdlib_contribs[1]} LoC "
            summary += "are removed from the ETS stdlib"
            summary += ".\n\n"

        return summary

    def rawSummary(self) -> list[str]:
        """Returns a list of strings, each item being a short file summary."""

        raw = list[str]()
        for fi in self.file_facts:
            summary = fi.new_name
            if fi.state == "removed":
                summary = fi.old_name

            summary += ": "
            summary += f"{fi.state} file (contributes to: {fi.type}), "
            summary += f"{fi.num_added_lines} lines added, "
            summary += f"{fi.num_removed_lines} lines removed, "
            summary += f"{fi.num_added_assertions} assertions added, "
            summary += f"{fi.num_removed_assertions} assertions removed, "
            summary += f"{fi.num_added_cte_checks} CTE checks added, "
            summary += f"{fi.num_removed_cte_checks} CTE checks removed"

            raw.append(summary)
        return raw


__all__ = ["PatchAnalyzer", "FileInfo"]
