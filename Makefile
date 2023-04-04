SHELL := /bin/bash

# List of targets the `readme` target should call before generating the readme
export README_DEPS ?= docs/github-action.md

-include $(shell curl -sSL -o .build-harness "https://cloudposse.tools/build-harness"; echo .build-harness)

## Lint terraform code
lint:
	$(SELF) terraform/install terraform/get-modules terraform/get-plugins terraform/lint terraform/validate

install-deps:
	pip install -r src/requirements.txt

prep-fixtures:
	pushd src/tests/fixtures/terraform-aws-components && \
    git init && \
    git config --global user.email "you@example.com" && \
    git config --global user.name "Your Name" && \
    git checkout -b main && \
    git add . && \
    git commit -m "update" && \
    git tag 10.2.1 || true && \
    popd

	pushd src/tests/fixtures/terraform-aws-components-02-invalid-no-tags && \
    git init || true && \
    popd

test:
	pytest -s -v --pyargs src/