import logging
import subprocess
from atmos_component import AtmosComponent


class ToolExecutionError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(message)


def atmos_vendor_component(component: AtmosComponent):
    command = ["atmos", "vendor", "pull", "-c", component.get_name()]
    response = subprocess.run(command, capture_output=True, cwd=component.get_infra_repo_dir())

    if response.returncode != 0:
        error_message = response.stderr.decode("utf-8")
        raise ToolExecutionError(error_message)

    logging.debug(f"Successfully vendored component: {component.get_name()}")


def diff(file1: str, file2: str):
    command = ["diff", file1, file2]

    logging.debug(f"Executing: '{' '.join(command)}' ... ")

    response = subprocess.run(command, capture_output=True)

    if response.returncode != 0:
        error_message = response.stderr.decode("utf-8")
        logging.error(error_message)

    result = response.stdout

    return result.strip().decode("utf-8") if result else None


def go_getter_pull_component_repo(go_getter_tool: str, component: AtmosComponent, destination_dir: str, download_dir: str):
    command = [go_getter_tool, component.get_uri_repo(), destination_dir]

    logging.debug(f"Executing: '{' '.join(command)}' ... ")

    response = subprocess.run(command, capture_output=True, cwd=download_dir)

    if response.returncode != 0:
        error_message = response.stderr.decode("utf-8")
        raise ToolExecutionError(error_message)

    logging.debug(f"Pulled whole component repo successfully: {component.get_uri_repo()}")


def git_get_latest_tag(git_dir: str):
    command = ["git", "describe", "--tags", "--abbrev=0"]

    logging.debug(f"Executing: '{' '.join(command)}' ... ")

    response = subprocess.run(command, capture_output=True, cwd=git_dir)

    if response.returncode != 0:
        error_message = response.stderr.decode("utf-8")
        return None

    tag = response.stdout

    return tag.strip().decode("utf-8") if tag else None
