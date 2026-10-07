# Mender service image: HTTP API over the pipeline.
# Full runs additionally need docker (sandbox) and a reachable cluster:
#   docker run --env-file .env -v /var/run/docker.sock:/var/run/docker.sock \
#     -p 8080:8080 mender
FROM python:3.12-slim

ARG KUBECTL_VERSION=v1.37.1
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl \
    && rm -rf /var/lib/apt/lists/* \
    && curl -fsSLo /usr/local/bin/kubectl \
        "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/amd64/kubectl" \
    && chmod +x /usr/local/bin/kubectl

WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install --no-cache-dir .
# `mender serve` reads mender.yaml from the working directory at startup. The file
# holds no secrets; mount a different one at /app/mender.yaml to change the config.
COPY mender.yaml ./

ENV PYTHONUNBUFFERED=1
EXPOSE 8080
CMD ["mender", "serve", "--host", "0.0.0.0", "--port", "8080"]
