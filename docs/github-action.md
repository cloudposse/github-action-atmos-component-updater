<!-- markdownlint-disable -->

## Inputs

| Name | Description | Default | Required |
|------|-------------|---------|----------|
| atmos-version | Atmos version to use for vendoring. Default 'latest' | latest | false |
| dry-run | Skip creation of remote branches and pull requests. Only print list of affected componented into file that is defined in 'outputs.affected-components-file' | false | false |
| exclude | Comma or new line separated list of component names to exclude. For example: 'vpc,eks/\*,rds'. By default no components are excluded. Default '' |  | false |
| github-access-token | GitHub Token used to perform git and GitHub operations | ${{ github.token }} | false |
| include | Comma or new line separated list of component names to include. For example: 'vpc,eks/\*,rds'. By default all components are included. Default '\*' | \* | false |
| infra-terraform-dirs | Comma or new line separated list of terraform directories in infra repo. For example 'components/terraform,components/terraform-old. Default 'components/terraform' | components/terraform | false |
| log-level | Log level for this action. Default 'INFO' | INFO | false |
| max-number-of-prs | Number of PRs to create. Maximum is 10. | 10 | false |
| pr-body-template | A string representing a Jinja2 formatted template to be used as the content of a Pull Request (PR) body. If not set template from `src/templates/pr\_body.j2.md` will be used |  | false |
| pr-labels | Comma or new line separated list of labels that will added on PR creation. Default: `component-update` | component-update | false |
| pr-title-template | A string representing a Jinja2 formatted template to be used as the content of a Pull Request (PR) title. If not, set template from `src/templates/pr\_title.j2.md` will be used |  | false |
| vendoring-enabled | Do not perform 'atmos vendor component-name' on components that wasn't vendored | true | false |


## Outputs

| Name | Description |
|------|-------------|
| affected | The affected components |
| has-affected-stacks | Whether there are affected components |
<!-- markdownlint-restore -->
