import logging
import click
from github import Github
from component_updater import ComponentUpdater
from github_provider import GitHubProvider
from tools_manager import ToolsManager
from config import Config


def main(github_api_token: str, config: Config):
    github_provider = GitHubProvider(config, Github(github_api_token))
    tools_manager = ToolsManager(config.go_getter_tool)

    for infra_terraform_dir in config.infra_terraform_dirs:
        component_updater = ComponentUpdater(github_provider, tools_manager, infra_terraform_dir, config)
        component_updater.update()


@click.command()
@click.option('--github-api-token',
              envvar='REPO_ACCESS_TOKEN',
              required=True,
              help="GitHub API token")
@click.option('--infra-repo-name',
              required=True,
              help="Organization and repo in format '<organization>/<infra-repo-name>' for infra. For example 'cloudposse/infra-live'")
@click.option('--infra-repo-dir',
              required=True,
              help="Path to cloned infra/repo")
@click.option('--infra-terraform-dirs',
              required=True,
              show_default=True,
              default='components/terraform',
              help="Comma or new line separated list of terraform directories in infra repo. For example 'components/terraform/gcp,components/terraform/aws")
@click.option('--skip-component-vendoring',
              required=True,
              show_default=True,
              default=False,
              help="Do not perform 'atmos vendor <component-name>' on components that wasn't vendored")
@click.option('--max-number-of-prs',
              required=True,
              show_default=True,
              default=10,
              help="Number of PRs to create. Maximum is 10.")
@click.option('--include',
              required=True,
              default='*',
              show_default=True,
              help="Comma or new line separated list of component names to include. For example: 'vpc,eks/*,rds'. By default all components are included")
@click.option('--exclude',
              required=True,
              default='',
              show_default=True,
              help="Comma or new line separated list of component names to exclude. For example: 'vpc,eks/*,rds'. By default no components are excluded")
@click.option('--go-getter-tool',
              required=True,
              help="Path to go-getter")
@click.option('--log-level',
              default='INFO',
              show_default=True,
              required=False,
              help="Log Level: [CRITICAL|ERROR|WARNING|INFO|DEBUG]")
@click.option('--dry-run',
              required=False,
              show_default=True,
              default=False,
              help="Skip creation of remote branches and pull requests. Only print list of affected componented into file that is defined in --affected-components-file, Default: false.")
@click.option('--affected-components-file',
              required=False,
              show_default=True,
              default="affected_components.json",
              help="Path to output file that will contain list of affected components in json format")
@click.option('--pr-title-template',
              required=False,
              show_default=True,
              default="",
              help="Template in Python's Jinja2 format to use for PR title. If not set template from `src/templates/pr_title.j2.md` will be used")
@click.option('--pr-body-template',
              required=False,
              show_default=True,
              default="",
              help="Template in Python's Jinja2 format to use for PR body. If not set template from `src/templates/pr_body.j2.md` will be used")
@click.option('--pr-labels',
              required=False,
              show_default=True,
              default="component-update",
              help="Comma or new line separated list of labels that will added on PR creation. Default: component-update")
def cli_main(github_api_token,
             infra_repo_name,
             infra_repo_dir,
             infra_terraform_dirs,
             skip_component_vendoring,
             max_number_of_prs,
             include,
             exclude,
             go_getter_tool,
             log_level,
             dry_run,
             affected_components_file,
             pr_title_template,
             pr_body_template,
             pr_labels):
    logging.basicConfig(format='[%(asctime)s] %(levelname)-7s %(message)s',
                        datefmt='%d-%m-%Y %H:%M:%S',
                        level=logging.getLevelName(log_level))

    config = Config(infra_repo_name,
                    infra_repo_dir,
                    infra_terraform_dirs,
                    skip_component_vendoring,
                    max_number_of_prs,
                    include,
                    exclude,
                    go_getter_tool,
                    dry_run,
                    affected_components_file,
                    pr_title_template,
                    pr_body_template,
                    pr_labels)

    logging.info(f'Using configuration: {config}')

    main(github_api_token, config)


if __name__ == "__main__":
    # pylint: disable=no-value-for-parameter
    cli_main()
