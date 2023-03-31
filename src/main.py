import logging
import click
import sys

from component_updater import ComponentUpdater, ComponentUpdaterError
from github_provider import GitHubProvider
from utils.tools import ToolExecutionError


def main(github_api_token, infra_repo_name, infra_repo_dir, go_getter_tool):
    github_provider = GitHubProvider(github_api_token, infra_repo_name)

    component_updater = ComponentUpdater(github_provider, infra_repo_dir, go_getter_tool)

    try:
        component_updater.update()
    except (ComponentUpdaterError, ToolExecutionError) as e:
        logging.error(e.message)
        sys.exit(1)


@click.command()
@click.option('--github-api-token', envvar='REPO_ACCESS_TOKEN', required=True, help="GitHub API token")
@click.option('--infra-repo-name', required=True,
              help="Organization and repo in format '<organization>/<infra-repo-name>' for infra. For example 'cloudposse/infra-live'")
@click.option('--infra-repo-dir', required=True, help="Path to cloned infra/repo")
@click.option('--go-getter-tool', required=True, help="Path to go-getter")
@click.option('--log-level', default='INFO', required=False, help="Log Level: [CRITICAL|ERROR|WARNING|INFO|DEBUG]")
def cli_main(github_api_token, infra_repo_name, infra_repo_dir, go_getter_tool, log_level):
    logging.basicConfig(format='[%(asctime)s] %(levelname)-7s %(message)s',
                        datefmt='%d-%m-%Y %H:%M:%S',
                        level=logging.getLevelName(log_level))

    main(github_api_token, infra_repo_name, infra_repo_dir, go_getter_tool)


if __name__ == "__main__":
    cli_main()
