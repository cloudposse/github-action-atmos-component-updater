#!/bin/bash

set -e

export GO_GETTER_TOOL="/root/go/bin/go-getter"

# Install the requested atmos version if specified
if [ -n "$ATMOS_VERSION" ] && [ "$ATMOS_VERSION" != "latest" ]; then
    echo "Installing atmos version ${ATMOS_VERSION}..."
    apt-get update -qq > /dev/null 2>&1
    apt-get install -y -qq atmos="${ATMOS_VERSION}-*" > /dev/null 2>&1
fi

cd /github/action/

python3 src/main.py \
    --github-api-token ${GITHUB_ACCESS_TOKEN} \
    --go-getter-tool ${GO_GETTER_TOOL} \
    --infra-repo-name ${GITHUB_REPOSITORY} \
    --infra-repo-dir ${INFRA_REPO_DIR} \
    --infra-terraform-dirs "${INFRA_TERRAFORM_DIRS}" \
    --vendoring-enabled ${VENDORING_ENABLED} \
    --max-number-of-prs ${MAX_NUMBER_OF_PRS} \
    --include "${INCLUDE}" \
    --exclude "${EXCLUDE}" \
    --log-level ${LOG_LEVEL} \
    --dry-run ${DRY_RUN} \
    --pr-labels "${PR_LABELS}" \
    --pr-title-template "${PR_TITLE_TEMPLATE}" \
    --pr-body-template "${PR_BODY_TEMPLATE}" \
    --affected-components-file 'affected-components.json'

cat affected-components.json
affected=$(jq -c '.' < affected-components.json)
echo "affected=$affected" >> $GITHUB_OUTPUT

[[ "$affected" == "[]" ]] && has_affected_stacks=true || has_affected_stacks=false
echo "has-affected-stacks=$has_affected_stacks" >> $GITHUB_OUTPUT
