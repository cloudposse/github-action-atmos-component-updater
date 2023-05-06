#!/bin/bash

set -ex

echo "----------------------"
echo "GITHUB_REPOSITORY=${GITHUB_REPOSITORY}"
echo "GITHUB_WORKSPACE=${GITHUB_WORKSPACE}"
pwd
echo "----------------------"
ls -l /github/
echo "----------------------"
ls -l /github/workspace/
echo "----------------------"
ls -l /
echo "----------------------"

# export GO_GETTER_TOOL="$(go env GOPATH)/bin/go-getter"

# python src/main.py \
#     --github-api-token ${GITHUB_ACCESS_TOKEN} \
#     --go-getter-tool ${GO_GETTER_TOOL} \
#     --infra-repo-name ${GITHUB_REPOSITORY} \
#     --infra-repo-dir ${GITHUB_WORKSPACE} \
#     --infra-terraform-dirs ${INFRA_TERRAFORM_DIRS} \
#     --skip-component-vendoring ${SKIP_COMPONENT_VENDORING} \
#     --max-number-of-prs ${MAX_NUMBER_OF_PRS} \
#     --include "${INCLUDE}" \
#     --exclude "${EXCLUDE}" \
#     --log-level ${LOG_LEVEL} \
#     --dry-run ${DRY_RUN} \
#     --pr-labels "${PR_LABELS}" \
#     --pr-title-template "${PR_TITLE_TEMPLATE}" \
#     --pr-body-template "${PR_BODY_TEMPLATE}" \
#     --affected-components-file 'affected-components.json'