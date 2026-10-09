FROM python:3.13-alpine AS build
RUN apk add --no-cache git gcc musl-dev python3-dev libffi-dev openssl-dev cargo
WORKDIR /app
COPY requirements.txt .
RUN python -m venv venv
ENV PATH="/app/venv/bin/:$PATH"
RUN pip install -U pip
RUN pip install -r requirements.txt
FROM python:3.13-alpine
ARG APP_VERSION=dev
ARG NEW_INSTALLATION_ENDPOINT=dev
ARG NEW_HEARTBEAT_ENDPOINT=dev
# Non-root runtime user; /home/app is needed by keyring's file backend
RUN addgroup -S app && adduser -S -u 1000 -G app app \
    && mkdir -p /app /home/app \
    && chown app:app /app /home/app
WORKDIR /app
COPY --from=build --chown=app:app /app/venv /app/venv
# Libmagic is required at runtime by python-magic
RUN apk add --no-cache libmagic
ENV PATH="/app/venv/bin/:$PATH"
ENV PYTHONPATH /app
ENV NEW_INSTALLATION_ENDPOINT=$NEW_INSTALLATION_ENDPOINT
ENV NEW_HEARTBEAT_ENDPOINT=$NEW_HEARTBEAT_ENDPOINT
ENV APP_VERSION=$APP_VERSION
COPY --chown=app:app . /app/
USER app
CMD ["python", "-u", "./src/main.py"]
