import datetime
import urllib.request
import urllib.error
import json
import typing
import os
import http.client
import dotenv

from app.utils.authentication import generate_signature

dotenv.load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
LISTENER_PORT = os.getenv("LISTENER_PORT")
LISTENER_HOST = os.getenv("LISTENER_HOST") or "localhost"


def devagent_request(path: str, query_params: list[str]) -> typing.Any | None:
    if SECRET_KEY == None:
        raise Exception("SECRET_KEY not provided in .env file")

    if LISTENER_PORT == None:
        raise Exception("LISTENER_PORT not provided in .env file")

    url = f"http://{LISTENER_HOST}:{LISTENER_PORT}/{path}?{'&'.join(query_params)}"

    timestamp = str(datetime.datetime.now().timestamp())

    req = urllib.request.Request(url)
    req.add_header("timestamp", timestamp)
    req.add_header("sign", generate_signature(timestamp, SECRET_KEY))

    try:
        response: http.client.HTTPResponse = urllib.request.urlopen(req, timeout=30)
    except urllib.error.HTTPError as e:
        print(f"Server Error: {e.code}")
        print("Response Body:", e.read().decode("utf-8"))
        return None

    data = json.loads(response.read())
    response.close()

    return data
