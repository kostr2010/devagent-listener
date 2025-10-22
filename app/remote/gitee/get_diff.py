import urllib.request
import urllib.error
import urllib.parse
import json

from typing import Any, Mapping


def _convert_to_standard_diff(api_response: list) -> list[dict[str, str]]:
    """
    Convert Gitee API response to standard diff format.

    Args:
        api_response: Raw response from Gitee API

    Returns:
        List of dicts with 'file' and 'diff' keys
    """
    result = []

    for diff_item in api_response:
        patch = diff_item.get("patch")

        # Extract file path
        file_path = patch.get("new_path", "unknown")

        # Build standard diff format from the content
        diff_lines = []

        # Add diff header
        old_path = patch.get("old_path", file_path)
        new_path = patch.get("new_path", file_path)
        # FIXME: remove when not needed
        diff_lines.append(f"diff --git a/{old_path} b/{new_path}")
        diff_lines.append(f"--- a/{old_path}")
        diff_lines.append(f"+++ b/{new_path}")

        # Process text content
        text_lines = patch.get("diff", "").split("\n")

        for line_item in text_lines:
            diff_lines.append(line_item)

        # Join lines into a single diff string
        diff_str = "\n".join(diff_lines)

        result.append(
            {
                "file": file_path,
                "diff": diff_str,
                "added_lines": diff_item.get("additions", 0),
                "removed_lines": diff_item.get("deletions", 0),
            }
        )

    return result


def get_diff(token: str, url: str) -> Mapping[str, Any]:
    """
    Fetch Pull Request data from Gitee API.

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
        return {
            "error": "Missing required fields: owner, repo, and pr_number",
            "files": [],
        }

    # Construct API URL
    url = f"https://api.gitee.com/api/v5/repos/{owner}/{repo}/pulls/{pr_number}/files.json"

    try:
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
            return {"error": f"API returned error code: {data['code']}", "files": []}

        # Convert to standard diff format
        files = _convert_to_standard_diff(data)

        return {"repo": repo, "owner": owner, "pr_number": pr_number, "files": files}

    except urllib.error.HTTPError as e:
        return {"error": f"HTTP error {e.code}: {e.reason}", "files": []}
    except urllib.error.URLError as e:
        return {"error": f"URL error: {e.reason}", "files": []}
    except json.JSONDecodeError as e:
        return {"error": f"Failed to parse JSON response: {str(e)}", "files": []}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}", "files": []}
