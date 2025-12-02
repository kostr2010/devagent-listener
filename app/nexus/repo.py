import requests


class NexusRepo:
    _username: str
    _password: str
    _repo: str

    def __init__(self, username: str, password: str, repo: str):
        self._username = username
        self._password = password
        self._repo = repo

    def upload_file(self, local_path: str, remote_path: str) -> str:
        with open(local_path, "rb") as f:
            data = f.read()

        file_url = f"{self._repo}/{remote_path}"

        try:
            response = requests.put(
                file_url,
                auth=(self._username, self._password),
                data=data,
            )
        except Exception as e:
            raise e

        if not response.ok:
            raise Exception(
                f"Received error code {response.status_code}:{response.reason}"
            )

        return file_url
