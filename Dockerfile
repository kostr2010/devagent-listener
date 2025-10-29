FROM python:3.11

ARG DEVAGENT_PROVIDER
ARG DEVAGENT_MODEL
ARG DEVAGENT_API_KEY

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

RUN true > /.devagent.toml
RUN echo "provider = \"$DEVAGENT_PROVIDER\"" >> /.devagent.toml
RUN echo "model = \"$DEVAGENT_MODEL\"" >> /.devagent.toml
RUN echo "api_key = \"$DEVAGENT_API_KEY\"" >> /.devagent.toml
RUN echo "auto_approve_code = false" >> /.devagent.toml
