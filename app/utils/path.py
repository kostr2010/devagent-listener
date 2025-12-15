import os.path


def abspath_join(p1: str, p2: str) -> str:
    return os.path.abspath(os.path.join(p1, p2))


def is_subpath(path: str, subpath: str) -> bool:
    return os.path.normpath(path) == os.path.commonpath([path, subpath])
