import unittest

from app.patch.analyzer import PatchAnalyzer


class PatchAnalyzerTest(unittest.TestCase):
    def test_8860(self) -> None:
        pa = PatchAnalyzer("./tests/patch/8860.patch")
        assert pa.analyze()
        # print(pa.verboseFrontEndSummary())
        # print(pa.verboseTestSummary())
        # print("\n".join(pa.rawSummary()))


if __name__ == "__main__":
    unittest.main()
