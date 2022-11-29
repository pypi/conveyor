FROM python:alpine3.10 as build

RUN set -x \
    && python3 -m venv /opt/conveyor

ENV PATH="/opt/conveyor/bin:${PATH}"

RUN pip --no-cache-dir --disable-pip-version-check install --upgrade pip setuptools wheel

RUN apk update && apk add g++

COPY requirements.txt /tmp/requirements.txt

RUN set -x && pip --no-cache-dir --disable-pip-version-check install -r /tmp/requirements.txt


FROM python:alpine3.10

ENV PYTHONUNBUFFERED 1
ENV PYTHONPATH /opt/conveyor/src/
ENV PATH="/opt/conveyor/bin:${PATH}"

WORKDIR /opt/conveyor/src/

COPY --from=build /opt/conveyor/ /opt/conveyor/
COPY . /opt/conveyor/src/
