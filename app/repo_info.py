import dataclasses
import os.path
import os

from .config import app_settings


@dataclasses.dataclass
class RepoInfo:
    repo: str
    root: str
    rules_dir: str
    rules_config: str


REPO_RUNTIME_CORE = RepoInfo(
    repo="arkcompiler_runtime_core",
    root=os.path.abspath(app_settings.RUNTIME_CORE_ROOT),
    rules_dir=os.path.abspath(
        os.path.join(
            os.path.abspath(app_settings.RUNTIME_CORE_ROOT), "static_core/.REVIEW_RULES"
        )
    ),
    rules_config=os.path.abspath(
        os.path.join(
            os.path.abspath(app_settings.RUNTIME_CORE_ROOT), "static_core/REVIEW_RULES"
        )
    ),
)

REPO_ETS_FRONTEND = RepoInfo(
    repo="arkcompiler_ets_frontend",
    root=os.path.abspath(app_settings.ETS_FRONTEND_ROOT),
    rules_dir=os.path.abspath(
        os.path.join(
            os.path.abspath(app_settings.ETS_FRONTEND_ROOT), "ets2panda/.REVIEW_RULES"
        )
    ),
    rules_config=os.path.abspath(
        os.path.join(
            os.path.abspath(app_settings.ETS_FRONTEND_ROOT), "ets2panda/REVIEW_RULES"
        )
    ),
)

REPO_INFO = [REPO_RUNTIME_CORE, REPO_ETS_FRONTEND]
