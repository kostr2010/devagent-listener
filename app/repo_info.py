import dataclasses
import os.path
import os

from .config import app_settings


@dataclasses.dataclass
class RepoInfo:
    repo: str
    rules_dir: str
    rules_config: str


REPO_RUNTIME_CORE = RepoInfo(
    repo="arkcompiler_runtime_core",
    rules_dir="static_core/.REVIEW_RULES",
    rules_config="static_core/REVIEW_RULES",
)

REPO_ETS_FRONTEND = RepoInfo(
    repo="arkcompiler_ets_frontend",
    rules_dir="ets2panda/.REVIEW_RULES",
    rules_config="ets2panda/REVIEW_RULES",
)

SUPPORTED_REPOS = [REPO_RUNTIME_CORE, REPO_ETS_FRONTEND]
