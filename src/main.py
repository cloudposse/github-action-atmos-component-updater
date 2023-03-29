import logging

import click
from component_updater import ComponentUpdater
from atmos_component import *
from github_provider import GitHubProvider

TERRAFORM_COMPONENTS_DIR = 'components/terraform'


def get_components(infra_components_dir):
    paths = []

    for root, dirs, files in os.walk(infra_components_dir):
        for file in files:
            if file == COMPONENT_YAML:
                paths.append(os.path.join(root, file))

    return paths


def main(github_api_token, new_version, infra_repo_name, infra_repo_dir):
    infra_components_dir = os.path.join(infra_repo_dir, TERRAFORM_COMPONENTS_DIR)
    component_files = get_components(infra_components_dir)

    github_provider = GitHubProvider(github_api_token, infra_repo_name)

    component_updater = ComponentUpdater(github_provider, infra_repo_dir, new_version)

    for component_file in component_files:
        component_updater.update(component_file)


@click.command()
@click.option('--github-api-token', envvar='REPO_ACCESS_TOKEN', required=True, help="GitHub API token")
@click.option('--infra-repo-name', required=True,
              help="Organization and repo in format '<organization>/<repo-name>' for example 'cloudposse/infra-main'")
@click.option('--infra-repo-dir', required=True, help="Path to cloned infra/repo")
@click.option('--components-version', required=True, help="Latest component version")
@click.option('--log-level', default='INFO', required=False, help="Log Level: [CRITICAL|ERROR|WARNING|INFO|DEBUG]")
def cli_main(github_api_token, infra_repo_name, infra_repo_dir, components_version, log_level):
    logging.basicConfig(format='[%(asctime)s] %(levelname)-7s %(message)s',
                        datefmt='%d-%m-%Y %H:%M:%S',
                        level=logging.getLevelName(log_level))

    main(github_api_token, components_version, infra_repo_name, infra_repo_dir)


if __name__ == "__main__":
    cli_main()
