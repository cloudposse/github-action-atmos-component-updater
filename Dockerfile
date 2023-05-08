FROM ubuntu:latest

ARG ATMOS_VERSION=1.34.2
ARG GO_VERSION=1.20
ARG PYTHON_VERSION=3.10
ARG NODE_VERSION=16

# Install the Cloud Posse Debian repository
RUN apt-get update && apt-get install -y apt-utils curl
RUN curl -1sLf 'https://dl.cloudsmith.io/public/cloudposse/packages/cfg/setup/bash.deb.sh' | bash

# Install Python
RUN apt-get install -y python${PYTHON_VERSION} python3-pip

# Install Go
RUN curl -O -L "https://golang.org/dl/go${GO_VERSION}.linux-amd64.tar.gz" && \
    tar -C /usr/local -xzf go${GO_VERSION}.linux-amd64.tar.gz && \
    rm go${GO_VERSION}.linux-amd64.tar.gz

# Install Node.js
RUN curl -fsSL https://deb.nodesource.com/setup_${NODE_VERSION}.x | bash - && \
    apt-get install -y nodejs

# Install Atmos
RUN apt-get install -y atmos="${ATMOS_VERSION}-*"

ADD . /github/action/
WORKDIR /github/action/

# Install Go Getter
RUN go mod download && \
    go mod download github.com/hashicorp/go-getter && \
    go install github.com/hashicorp/go-getter/cmd/go-getter

# Install Python Dependencies
RUN pip3 install -r src/requirements.txt

ENTRYPOINT [ "/github/action/entrypoint.sh" ]