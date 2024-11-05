import os
import logging
import subprocess

import semver

from atmos_component import AtmosComponent


class ToolExecutionError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(message)


class ToolsManager:
    def __init__(self, go_getter_tool: str):
        self.__go_getter_tool = go_getter_tool

    def atmos_vendor_component(self, component: AtmosComponent):
        os.environ['ATMOS_COMPONENTS_TERRAFORM_BASE_PATH'] = component.infra_terraform_dir
        command = ["atmos", "vendor", "pull", "-c", component.name]

        logging.info(f"Executing '{' '.join(command)}' for component version '{component.version}' ... ")

        response = subprocess.run(command, capture_output=True, cwd=component.infra_repo_dir, check=False)

        if response.returncode != 0:
            # atmos doesn't report error to stderr
            error_message = response.stderr.decode("utf-8") if response.stderr else response.stdout.decode("utf-8")
            logging.error(error_message)
            logging.debug(f"Component: {component}")
            # log to debug the file at infra_terraform_dir/component.name/component.yaml
            component_path = os.path.join(component.infra_terraform_dir, component.name, 'component.yaml')
            logging.debug(f"Content for {component_path}:")
            with open(component_path, 'r') as f:
                logging.debug(f.read())
            raise ToolExecutionError(error_message)

        logging.info(f"Successfully vendored component: {component.name}")

    def diff(self, file1: str, file2: str):
        command = ["diff", file1, file2]

        logging.debug(f"Executing: '{' '.join(command)}' ... ")

        response = subprocess.run(command, capture_output=True, check=False)

        if response.returncode != 0:
            error_message = response.stderr.decode("utf-8")
            logging.error(error_message)

        result = response.stdout

        return result.strip().decode("utf-8") if result else None

    def go_getter_pull_component_repo(self, component: AtmosComponent, destination_dir: str, download_dir: str):
        command = [self.__go_getter_tool, component.uri_repo, destination_dir]

        logging.debug(f"Executing: '{' '.join(command)}' ... ")

        response = subprocess.run(command, capture_output=True, cwd=download_dir, check=False)

        if response.returncode != 0:
            error_message = response.stderr.decode("utf-8")
            raise ToolExecutionError(error_message)

        logging.debug(f"Pulled whole component repo successfully: {component.uri_repo}")

    def git_get_latest_tag(self, git_dir: str):
        command = ["git", "for-each-ref", "--sort=-authordate", "--format", "'%(refname:short)'", "refs/tags"]

        logging.debug(f"Executing: '{' '.join(command)}' ... ")

        response = subprocess.run(command, capture_output=True, cwd=git_dir, check=False)

        if response.returncode != 0:
            error_message = response.stderr.decode("utf-8")
            logging.error(error_message)
            return None

        tags = response.stdout.split("\n")
        for tag in tags:
            try:
                semver.parse_version_info("tag")
                return tag.strip().decode("utf-8") if tag else None
            except Exception as e:
                logging.error(f"Error parsing tag: {tag} - {e}")
                continue

        return None

    def is_git_repo(self, repo_dir: str) -> bool:
        return os.path.exists(os.path.join(repo_dir, '.git'))
