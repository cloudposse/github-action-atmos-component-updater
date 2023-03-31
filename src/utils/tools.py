import logging
import subprocess


class ToolExecutionError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(message)


def atmos_vendor_component(infra_dir, component_name):
    command = ["atmos", "vendor", "pull", "-c", component_name]
    response = subprocess.run(command, capture_output=True, cwd=infra_dir)

    if response.returncode != 0:
        error_message = response.stderr.decode("utf-8")
        raise ToolExecutionError(error_message)

    logging.debug(f"Successfully vendored component: {component_name}")


def diff(file1, file2):
    command = ["diff", file1, file2]

    logging.debug(f"Executing: '{' '.join(command)}' ... ")

    response = subprocess.run(command, capture_output=True)

    if response.returncode != 0:
        error_message = response.stderr.decode("utf-8")
        raise ToolExecutionError(error_message)

    result = response.stdout

    return result.strip.decode("utf-8") if result else None


def go_getter_pull_component_repo(go_getter_tool, component, destination_dir, download_dir):
    command = [go_getter_tool, component.get_uri_repo(), destination_dir]

    logging.debug(f"Executing: '{' '.join(command)}' ... ")

    response = subprocess.run(command, capture_output=True, cwd=download_dir)

    if response.returncode != 0:
        error_message = response.stderr.decode("utf-8")
        raise ToolExecutionError(error_message)

    logging.debug(f"Pulled whole component repo successfully: {component.get_uri_repo()}")


def git_get_latest_tag(git_dir):
    command = ["git", "describe", "--tags", "--abbrev=0"]

    logging.debug(f"Executing: '{' '.join(command)}' ... ")

    response = subprocess.run(command, capture_output=True, cwd=git_dir)

    if response.returncode != 0:
        error_message = response.stderr.decode("utf-8")
        return None

    tag = response.stdout

    return tag.strip().decode("utf-8") if tag else None
