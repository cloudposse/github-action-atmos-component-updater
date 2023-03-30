import os
import logging
import subprocess


class ToolExecutionError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(message)


def atmos_vendor_pull(infra_dir, component_name):
    response = subprocess.run(["atmos", "vendor", "pull", "-c", component_name],
                              capture_output=True,
                              cwd=infra_dir)

    if response.returncode != 0:
        error_message = response.stderr.decode("utf-8")
        raise ToolExecutionError(error_message)
    else:
        logging.debug(f"Pulled component '{component_name}' successfully.")


def diff(file1, file2):
    response = subprocess.run(["diff", file1, file2], capture_output=True)

    if response.returncode != 0:
        error_message = response.stderr.decode("utf-8")
        raise ToolExecutionError(error_message)

    return response.stdout.decode("utf-8")


def go_getter(component, destination_dir):
    go_getter_path = os.environ.get('GO_GETTER_PATH')
    response = subprocess.run([go_getter_path, component.get_component_uri_repo(), destination_dir],
                              capture_output=True,
                              cwd=self.__download_dir)

    if response.returncode != 0:
        error_message = response.stderr.decode("utf-8")
        raise ToolExecutionError(error_message)
    else:
        logging.debug(f"Pulled repository for component '{component.get_name()}' successfully.")


def git_describe_tag(git_dir):
    response = subprocess.run(["git", "describe", "--tags", "--abbrev=0"],
                              capture_output=True,
                              cwd=git_dir)

    if response.returncode != 0:
        error_message = response.stderr.decode("utf-8")
        raise ToolExecutionError(error_message)

    return response.stdout.strip().decode("utf-8")
