FROM python:3.11

RUN pip install pip --upgrade

RUN apt update && apt upgrade -y

RUN apt install git

WORKDIR /

RUN git clone https://github.com/egavrin/devagent.git

WORKDIR /devagent

RUN pip install -e .

WORKDIR /devagent-listener

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY . .

RUN alembic upgrade head
