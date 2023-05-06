#!/bin/bash

set -ex

export GO_GETTER_TOOL="/usr/local/go/bin/go-getter"

cd /github/action/

python3 src/main.py \
    --github-api-token ${GITHUB_ACCESS_TOKEN} \
    --go-getter-tool ${GO_GETTER_TOOL} \
    --infra-repo-name ${GITHUB_REPOSITORY} \
    --infra-repo-dir /github/workspace/ \
    --infra-terraform-dirs ${INFRA_TERRAFORM_DIRS} \
    --skip-component-vendoring ${SKIP_COMPONENT_VENDORING} \
    --max-number-of-prs ${MAX_NUMBER_OF_PRS} \
    --include "${INCLUDE}" \
    --exclude "${EXCLUDE}" \
    --log-level ${LOG_LEVEL} \
    --dry-run ${DRY_RUN} \
    --pr-labels "${PR_LABELS}" \
    --pr-title-template "${PR_TITLE_TEMPLATE}" \
    --pr-body-template "${PR_BODY_TEMPLATE}" \
    --affected-components-file 'affected-components.json'