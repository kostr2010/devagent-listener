import os.path


def abspath_join(p1: str, p2: str) -> str:
    return os.path.abspath(os.path.join(p1, p2))
