FROM python:3.11

RUN apt update && apt upgrade -y

WORKDIR /ggw-devagent-sync

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .
