FROM ubuntu:jammy

ARG ATMOS_VERSION=1.99.0
ARG GO_VERSION=1.20
ARG PYTHON_VERSION=3.10

# Install the Cloud Posse Debian repository
RUN apt-get update && apt-get install -y apt-utils curl
RUN curl -1sLf 'https://dl.cloudsmith.io/public/cloudposse/packages/cfg/setup/bash.deb.sh' | bash

# Install Python
RUN apt-get install -y python${PYTHON_VERSION} python3-pip

# Install Go
RUN curl -O -L "https://golang.org/dl/go${GO_VERSION}.linux-amd64.tar.gz" && \
    tar -C /usr/local -xzf go${GO_VERSION}.linux-amd64.tar.gz && \
    rm go${GO_VERSION}.linux-amd64.tar.gz
ENV PATH="/usr/local/go/bin:${PATH}"

# Install Atmos
RUN apt-get install -y atmos="${ATMOS_VERSION}-*"

# Install Misc
RUN apt-get install -y git jq

ADD . /github/action/
WORKDIR /github/action/

# Install Go Getter
RUN go mod download && \
    go mod download github.com/hashicorp/go-getter && \
    go install github.com/hashicorp/go-getter/cmd/go-getter

# Install Python Dependencies
RUN pip3 install -r src/requirements.txt

ENTRYPOINT [ "/github/action/entrypoint.sh" ]
