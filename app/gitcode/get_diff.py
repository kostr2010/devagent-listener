import time
import pydantic
import urllib.request
import urllib.parse
import json
import typing


from app.config import CONFIG


class Summary(pydantic.BaseModel):
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
    project: str
    pr_number: int
    files: list[DiffFile]
    summary: Summary


def get_diff(url: str) -> Diff:
    if not "gitcode" in url:
        raise Exception(f"Unsupported remote passed as url : {url}")

    tries_left = 5
    should_retry = True

    while should_retry:
        try:
            diff = _try_get_diff(CONFIG.GITCODE_TOKEN, url)
        except Exception as e:
            if tries_left > 0:
                tries_left -= 1
                print(
                    f"[tries left: {tries_left}] Get diff for url {url} with the exception {str(e)}"
                )
                time.sleep(5 * (5 - tries_left))
            else:
                raise e
        else:
            should_retry = False

    return diff


###########
# private #
###########


def _try_get_diff(token: str, url: str) -> Diff:
    """
    Fetch Pull Request data from GitCode API.

    Args:
        payload: Contains 'owner', 'repo', 'number', and optional 'token' fields
        context: Tool execution context

    Returns:
        Dict with 'files' list containing file paths and diffs
    """

    parsed_url = urllib.parse.urlparse(url)
    url_path = parsed_url.path.split("/")

    # ['', 'owner', 'repo', 'pull', 'pr_number']
    owner = url_path[1]
    repo = url_path[2]
    pr_number = url_path[4]

    if not owner or not repo or not pr_number:
        raise Exception(
            f"Missing one or more of the required fields : owner={owner},repo={repo},pr_number={pr_number}"
        )

    # Construct API URL
    url = f"https://api.gitcode.com/api/v5/repos/{owner}/{repo}/pulls/{pr_number}/files.json"

    # Make HTTP request
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/json")

    # Add authentication token if provided
    if token:
        req.add_header("Authorization", f"Bearer {token}")

    with urllib.request.urlopen(req, timeout=30) as response:
        data = json.loads(response.read().decode("utf-8"))

    # Check for API errors
    if "code" in data and data["code"] != 0:
        raise Exception(f"API returned error code: {data['code']}")

    # Convert to standard diff format
    files = _convert_to_standard_diff(data)

    # Add summary information
    summary = Summary(
        total_files=int(data.get("count", 0)),
        added_lines=int(data.get("added_lines", 0)),
        removed_lines=int(data.get("remove_lines", 0)),
        base_sha=str(data.get("diff_refs", dict()).get("base_sha", "")),
        head_sha=str(data.get("diff_refs", dict()).get("head_sha", "")),
    )

    res = Diff(
        project=f"{owner}/{repo}",
        pr_number=int(pr_number),
        files=files,
        summary=summary,
    )

    return res


def _convert_to_standard_diff(api_response: dict[str, typing.Any]) -> list[DiffFile]:
    """
    Convert GitCode API response to standard diff format.

    Args:
        api_response: Raw response from GitCode API

    Returns:
        List of dicts with 'file' and 'diff' keys
    """
    result = list[DiffFile]()

    if "diffs" not in api_response:
        return result

    for diff_item in api_response["diffs"]:
        # Extract file path
        file_path = diff_item.get("statistic", dict()).get("path", "unknown")

        # Build standard diff format from the content
        diff_lines = list()

        # Add diff header
        old_path = diff_item.get("statistic", dict()).get("old_path", file_path)
        new_path = diff_item.get("statistic", dict()).get("new_path", file_path)
        # FIXME: remove when not needed
        diff_lines.append(f"diff --git a/{old_path} b/{new_path}")
        diff_lines.append(f"--- a/{old_path}")
        diff_lines.append(f"+++ b/{new_path}")

        # Process text content
        content = diff_item.get("content", dict())
        text_lines = content.get("text", list())

        for line_item in text_lines:
            line_content = line_item.get("line_content", "")
            line_type = line_item.get("type", "")

            # Handle different line types
            if line_type == "match":
                # Hunk header (e.g., @@ -0,0 +1,29 @@)
                diff_lines.append(line_content)
            elif line_type == "new":
                # Added line
                diff_lines.append(f"+{line_content}")
            elif line_type == "old":
                # Removed line
                diff_lines.append(f"-{line_content}")
            elif line_type == "context" or line_type == "":
                # Context line (unchanged)
                diff_lines.append(f" {line_content}")

        # Join lines into a single diff string
        diff_str = "\n".join(diff_lines)

        result.append(
            DiffFile(
                file=file_path,
                diff=diff_str,
                added_lines=diff_item.get("added_lines", 0),
                removed_lines=diff_item.get("remove_lines", 0),
            )
        )

    return result
