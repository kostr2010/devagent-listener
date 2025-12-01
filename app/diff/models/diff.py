import pydantic


class DiffSummary(pydantic.BaseModel):
    total_files: int
    added_lines: int
    removed_lines: int
    base_sha: str
    head_sha: str


class DiffFile(pydantic.BaseModel):
    file: str
    diff: str
    added_lines: int
    removed_lines: int


class Diff(pydantic.BaseModel):
    remote: str
    project: str
    files: list[DiffFile]
    summary: DiffSummary
