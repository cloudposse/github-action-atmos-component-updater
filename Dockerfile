FROM ubuntu:latest

ARG ATMOS_VERSION=1.34.2

# RUN apt-get update

# # Install Python 3.10
# RUN apt-get install -y python3.10 && \
#     apt-get install -y python3-pip

# # Install Go 1.20
# RUN apt-get install -y wget && \
#     wget https://golang.org/dl/go1.20.linux-amd64.tar.gz && \
#     tar -C /usr/local -xzf go1.20.linux-amd64.tar.gz && \
#     rm go1.20.linux-amd64.tar.gz
# ENV PATH="/usr/local/go/bin:${PATH}"

# # Install Node.js 16.x
# RUN apt-get install -y curl && \
#     curl -fsSL https://deb.nodesource.com/setup_16.x | bash - && \
#     apt-get install -y nodejs

# # Install Atmos
# RUN apt-get install -y apt-utils curl && \
#     curl -1sLf 'https://dl.cloudsmith.io/public/cloudposse/packages/cfg/setup/bash.deb.sh' > /tmp/cloudsmith.sh && \
#     bash /tmp/cloudsmith.sh && \
#     rm /tmp/cloudsmith.sh && \
#     apt-get install atmos

ADD . /github/action/

WORKDIR /github/action/

# # Install Go Getter
# RUN go mod download && \
#     go install github.com/hashicorp/go-getter/cmd/go-getter

# ADD src/requirements.txt requirements.txt

# # Install Python Dependencies
# RUN pip3 install -r requirements.txt

# VOLUME /app

ENTRYPOINT [ "/github/action/github-entrypoint.sh" ]