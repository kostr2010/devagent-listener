import functools
import logging
import time

from .gitcode.get_diff import get_diff as get_gitcode_diff
from .gitee.get_diff import get_diff as get_gitee_diff

from app.config import CONFIG


def get_diff(url: str):
    log = logging.getLogger(__name__)
    log.setLevel(logging.INFO)

    cb = None
    if "gitcode" in url:
        cb = functools.partial(get_gitcode_diff, CONFIG.GITCODE_TOKEN)
    elif "gitee" in url:
        cb = functools.partial(get_gitee_diff, CONFIG.GITEE_TOKEN)

    diff = None
    tries_left = 5
    should_retry = True

    while should_retry:
        diff = cb(url)
        if diff == None or ("error" in diff and tries_left > 0):
            tries_left -= 1
            log.info(
                f"[tries left: {tries_left}] Get diff for url {url} with the exception {diff['error']}"
            )
            time.sleep(5 * (5 - tries_left))
        else:
            should_retry = False

    return diff
