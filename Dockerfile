FROM python:3.12.4-slim-bookworm as build

RUN set -x \
    && python3 -m venv /opt/conveyor

ENV PATH="/opt/conveyor/bin:${PATH}"

RUN pip --no-cache-dir --disable-pip-version-check install --upgrade pip setuptools wheel

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    set -x \
    && apt-get update \
    && apt-get install --no-install-recommends -y \
    build-essential

COPY requirements.txt /tmp/requirements.txt

RUN --mount=type=cache,target=/root/.cache/pip \
    set -x \
    && pip --no-cache-dir --disable-pip-version-check \
    install -r /tmp/requirements.txt


FROM python:3.12.4-slim-bookworm

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH /opt/conveyor/src/
ENV PATH="/opt/conveyor/bin:${PATH}"

WORKDIR /opt/conveyor/src/

COPY --from=build /opt/conveyor/ /opt/conveyor/
COPY . /opt/conveyor/src/
