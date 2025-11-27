FROM python:3.11

RUN pip install pip --upgrade --timeout 300
RUN apt update && apt upgrade -y
RUN apt install git

WORKDIR /

RUN git clone https://github.com/egavrin/devagent.git

WORKDIR /devagent

RUN pip install -e . --timeout 300

WORKDIR /devagent-listener

COPY . .

RUN pip install -r requirements.txt --timeout 300
