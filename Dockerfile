FROM ubuntu:latest

ARG ATMOS_VERSION=latest

RUN apt-get update

# Install Python 3.10
RUN apt-get install -y python3.10

# Install Go 1.20
RUN apt-get install -y wget && \
    wget https://golang.org/dl/go1.20.linux-amd64.tar.gz && \
    tar -C /usr/local -xzf go1.20.linux-amd64.tar.gz && \
    rm go1.20.linux-amd64.tar.gz
ENV PATH="/usr/local/go/bin:${PATH}"

# Install Node.js 16.x
RUN apt-get install -y curl && \
    curl -fsSL https://deb.nodesource.com/setup_16.x | bash - && \
    apt-get install -y nodejs

# Install Atmos
RUN apt-get install -y apt-utils curl && \
    curl -1sLf 'https://dl.cloudsmith.io/public/cloudposse/packages/cfg/setup/bash.deb.sh' │ bash && \
    apt-get install atmos@="${ATMOS_VERSION}"

WORKDIR /app

ADD . .

# Install Go Getter
RUN go mod download && \
    go install github.com/hashicorp/go-getter/cmd/go-getter && \
    export GO_GETTER_TOOL="$(go env GOPATH)/bin/go-getter"

# Install Python Dependencies
RUN pip install -r src/requirements.txt

ENTRYPOINT ["./entrypoint.sh"]