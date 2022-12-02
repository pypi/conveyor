FROM python:3.11.0-slim-buster as build

RUN set -x \
    && python3 -m venv /opt/conveyor

ENV PATH="/opt/conveyor/bin:${PATH}"

RUN pip --no-cache-dir --disable-pip-version-check install --upgrade pip setuptools wheel

RUN set -x \
    && apt-get update \
    && apt-get install --no-install-recommends -y \
    build-essential

COPY requirements.txt /tmp/requirements.txt

RUN set -x && pip --no-cache-dir --disable-pip-version-check install -r /tmp/requirements.txt


FROM python:3.11.0-slim-buster

ENV PYTHONUNBUFFERED 1
ENV PYTHONPATH /opt/conveyor/src/
ENV PATH="/opt/conveyor/bin:${PATH}"

WORKDIR /opt/conveyor/src/

COPY --from=build /opt/conveyor/ /opt/conveyor/
COPY . /opt/conveyor/src/
