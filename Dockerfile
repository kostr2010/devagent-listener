FROM python:3.11

ARG DEVAGENT_REVISION
ARG DEVAGENT_PROVIDER
ARG DEVAGENT_MODEL
ARG DEVAGENT_API_KEY

RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

WORKDIR /

RUN true > .devagent.toml
RUN echo "provider = \"${DEVAGENT_PROVIDER}\"" >> .devagent.toml
RUN echo "model = \"${DEVAGENT_MODEL}\"" >> .devagent.toml
RUN echo "[providers.${DEVAGENT_PROVIDER}]" >> .devagent.toml
RUN echo "api_key = \"${DEVAGENT_API_KEY}\"" >> .devagent.toml

RUN mkdir devagent

WORKDIR /devagent

RUN git init .
RUN git remote add origin https://github.com/egavrin/devagent.git
RUN git fetch origin ${DEVAGENT_REVISION}
RUN git checkout ${DEVAGENT_REVISION}
RUN pip install -e . --timeout 300

WORKDIR /devagent-listener

COPY . .

RUN pip install -r requirements.txt --timeout 300
