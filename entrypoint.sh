#!/bin/env/bash

echo ${GO_GETTER_TOOL}

# python src/main.py \
#     --github-api-token ${GITHUB_ACCESS_TOKEN} \
#     --go-getter-tool ${GO_GETTER_TOOL} \
#     --infra-repo-name ${{ github.repository }} \
#     --infra-repo-dir ${{ github.workspace }} \
#     --infra-terraform-dirs ${{ inputs.infra-terraform-dirs }} \
#     --skip-component-vendoring ${{ inputs.skip-component-vendoring }} \
#     --max-number-of-prs ${{ inputs.max-number-of-prs }} \
#     --include "${{ inputs.include }}" \
#     --exclude "${{ inputs.exclude }}" \
#     --log-level ${{ inputs.log-level }} \
#     --dry-run ${{ inputs.dry-run }} \
#     --pr-labels "${{ inputs.pr-labels }}" \
#     --pr-title-template "${{ inputs.pr-title-template }}" \
#     --pr-body-template "${{ inputs.pr-body-template }}" \
#     --affected-components-file 'affected-components.json'