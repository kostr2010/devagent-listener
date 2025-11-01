import subprocess
import git
import time


def clone(url: str, branch: str, dir: str, retries: int = 5) -> None:
    should_retry = True
    tries_left = retries

    while should_retry:
        try:
            git.Repo.clone_from(
                url,
                dir,
                allow_unsafe_protocols=True,
                branch=branch,
                depth=1,
            )
        except Exception as e:
            if tries_left > 0:
                tries_left -= 1
                print(
                    f"[tries left: {tries_left}] Repo clone failed with the exception {e}"
                )
                time.sleep(5 * (5 - tries_left))
            else:
                raise e
        else:
            should_retry = False


def get_revision(root: str) -> str:
    cmd = ["git", "-C", root, "rev-parse", "HEAD"]

    res = subprocess.run(
        cmd,
        capture_output=True,
    )

    assert res.returncode == 0
    stdout = res.stdout.decode("utf-8")

    return stdout.strip()
