import os
import logging
import subprocess
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
        command = ["git", "describe", "--tags", "--abbrev=0"]

        logging.debug(f"Executing: '{' '.join(command)}' ... ")

        response = subprocess.run(command, capture_output=True, cwd=git_dir, check=False)

        if response.returncode != 0:
            error_message = response.stderr.decode("utf-8")
            logging.error(error_message)
            return None

        tag = response.stdout

        return tag.strip().decode("utf-8") if tag else None

    def git_log_between_versions(self, git_dir:str, component_path: str, previous_ref: str, future_ref: str = 'main'):
        command = ["git", "log", "--pretty=format:%s", f"{previous_ref}..{future_ref}", component_path]

        logging.debug(f"Executing: '{' '.join(command)}' ... ")

        response = subprocess.run(command, capture_output=True, cwd=git_dir, check=False)

        if response.returncode != 0:
            error_message = response.stderr.decode("utf-8")
            logging.error(error_message)
            return None

        log = response.stdout

        return log.strip().decode("utf-8") if log else None

    def is_git_repo(self, repo_dir: str) -> bool:
        return os.path.exists(os.path.join(repo_dir, '.git'))
