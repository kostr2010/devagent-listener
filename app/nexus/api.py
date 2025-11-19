import requests

from app.config import CONFIG


def upload_file_to_nexus(path_to_file: str, remote_path: str) -> str:
    with open(path_to_file, "rb") as f:
        data = f.read()

    file_url = f"{CONFIG.NEXUS_REPO_URL}/{remote_path}"

    try:
        response = requests.put(
            file_url,
            auth=(CONFIG.NEXUS_USERNAME, CONFIG.NEXUS_PASSWORD),
            data=data,
        )
    except Exception as e:
        raise e

    if not response.ok:
        raise Exception(f"Received error code {response.status_code}:{response.reason}")

    return file_url
