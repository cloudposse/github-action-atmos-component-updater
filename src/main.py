import sys
import logging
import click

from component_updater import ComponentUpdater, ComponentUpdaterError
from github_provider import GitHubProvider
from tools import ToolExecutionError


def main(github_api_token: str,
         infra_repo_name: str,
         infra_repo_dir: str,
         infra_terraform_dirs: str,
         includes: str,
         excludes: str,
         go_getter_tool: str):
    github_provider = GitHubProvider(github_api_token, infra_repo_name)

    for infra_terraform_dir in infra_terraform_dirs.split(','):
        component_updater = ComponentUpdater(github_provider,
                                             infra_repo_dir,
                                             infra_terraform_dir,
                                             includes,
                                             excludes,
                                             go_getter_tool)

        try:
            component_updater.update()
        except (ComponentUpdaterError, ToolExecutionError) as error:
            logging.error(error.message)
            sys.exit(1)


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
              default='components/terraform',
              help="CSV list of terraform directories in infra repo. For example 'components/terraform,components/terraform2")
@click.option('--includes',
              required=False,
              help="CSV list of component names to include. For example: 'vpc,eks/*,rds'. By default all components are included")
@click.option('--excludes',
              required=False,
              help="CSV list of component names to exclude. For example: 'vpc,eks/*,rds'. By default no components are excluded")
@click.option('--go-getter-tool',
              required=True,
              help="Path to go-getter")
@click.option('--log-level',
              default='INFO',
              required=False,
              help="Log Level: [CRITICAL|ERROR|WARNING|INFO|DEBUG]")
def cli_main(github_api_token, infra_repo_name, infra_repo_dir, infra_terraform_dirs, includes, excludes, go_getter_tool, log_level):
    logging.basicConfig(format='[%(asctime)s] %(levelname)-7s %(message)s',
                        datefmt='%d-%m-%Y %H:%M:%S',
                        level=logging.getLevelName(log_level))

    main(github_api_token, infra_repo_name, infra_repo_dir, infra_terraform_dirs, includes, excludes, go_getter_tool)


if __name__ == "__main__":
    # pylint: disable=no-value-for-parameter
    cli_main()
