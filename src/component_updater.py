import logging
import os
from utils import io
from atmos_component import AtmosComponent, COMPONENT_YAML
import subprocess
from github_provider import GitHubProvider
from git_provider import GitProvider

COMMIT_MESSAGE_TEMPLATE = "Updated component '{component_name}' to version '{component_version}'"


class ComponentUpdater:
    def __init__(self, github_provider: GitHubProvider, infra_repo_dir: str, new_version: str):
        self.__github_provider = github_provider
        self.__infra_repo_dir = infra_repo_dir
        self.__new_version = new_version

    def update(self, component_file: str):
        original_component = AtmosComponent(self.__infra_repo_dir, component_file)

        logging.info(f"Processing component: {original_component.get_name()}")

        if self.__is_already_updated(original_component):
            logging.info(f"Component already updated: {original_component.get_name()}")
            return

        updated_component = self.__clone_infra_for_component(original_component)

        if self.__has_component_not_been_pulled(updated_component):
            logging.debug(f"Component was not pulled: {original_component.get_name()}")
            updated_component.update_version(self.__new_version)
            updated_component.persist()
            self.__update_component(original_component, updated_component)
            return

        rendered_component = self.__clone_infra_for_component(original_component)
        rendered_component.update_version(self.__new_version)
        io.remove_all_from_dir(rendered_component.get_component_dir())
        rendered_component.persist()

        self.__execute_atmos_vendor_pull(rendered_component.get_infra_repo_dir(), rendered_component.get_name())

        rendered_component_files = io.get_filenames_in_dir(rendered_component.get_component_dir(), ['**/*'])

        can_auto_update = True

        for rendered_file in rendered_component_files:
            # skip "component.yaml" or ends with .md
            if rendered_file.endswith(COMPONENT_YAML) or rendered_file.endswith('.md'):
                continue

            relative_path = os.path.relpath(rendered_file, rendered_component.get_infra_repo_dir())
            original_file = os.path.join(updated_component.get_infra_repo_dir(), relative_path)

            if not os.path.isfile(original_file):
                logging.warning(f"File doesn't exist: {relative_path}")
                can_auto_update = False
                break

            if io.calc_file_md5_hash(original_file) != io.calc_file_md5_hash(rendered_file):
                logging.warning(f"File has changed: {relative_path}")
                logging.debug(f"diff: " + self.__execute_diff(original_file, rendered_file))
                can_auto_update = False
                break

        if can_auto_update:
            updated_component.update_version(self.__new_version)
            updated_component.persist()
            self.__update_component(original_component, updated_component)
        else:
            logging.warning(f"Component can not be updated: {updated_component.get_name()}")

    def __is_already_updated(self, component: AtmosComponent):
        return component.get_version() == self.__new_version

    def __has_component_not_been_pulled(self, component: AtmosComponent):
        updated_component_files = io.get_filenames_in_dir(component.get_component_dir(), ['**/*'])
        return len(updated_component_files) == 1 and updated_component_files[0].endswith(COMPONENT_YAML)

    def __clone_infra_for_component(self, component):
        update_infra_repo_dir = io.create_tmp_dir()
        logging.debug(f"Infra repo dir: {update_infra_repo_dir}")
        io.copy_dirs(self.__infra_repo_dir, update_infra_repo_dir)
        component_file = os.path.join(update_infra_repo_dir, component.get_relative_path())
        return AtmosComponent(update_infra_repo_dir, component_file)

    def __update_component(self, original_component, updated_component):
        logging.info(f"Updating component: {updated_component.get_name()}")

        git_provider = GitProvider(updated_component.get_infra_repo_dir())

        branch_name = git_provider.get_component_branch_name(updated_component.get_name(), self.__new_version)
        remote_branch_name = f'origin/{branch_name}'

        if git_provider.branch_exists(branch_name) or git_provider.branch_exists(remote_branch_name):
            logging.warning(f"Branch '{branch_name}' already exists. Skipping")
            return

        git_provider.create_branch_and_push_all_changes(branch_name,
                                                        COMMIT_MESSAGE_TEMPLATE.format(
                                                            component_name=updated_component.get_name(),
                                                            component_version=updated_component.get_version()))

        logging.info(f"Opening PR for branch {branch_name}")

        pr = self.__github_provider.open_pr(branch_name,
                                            updated_component.get_name(),
                                            original_component.get_version(),
                                            updated_component.get_version())
        logging.info(f"Opened PR #{pr.number}")

        opened_prs = self.__github_provider.get_open_prs_for_component(updated_component.get_name())

        for opened_pr in opened_prs:
            if opened_pr.number != pr.number:
                closing_message = f"Closing in favor of PR #{pr.number}"
                self.__github_provider.close_pr(opened_pr, closing_message)
                logging.info(f"Closed pr {opened_pr.number} in favor of #{pr.number}")

    def __execute_atmos_vendor_pull(self, infra_dir, component_name):
        response = subprocess.run(["atmos", "vendor", "pull", "-c", component_name],
                                  capture_output=True,
                                  cwd=infra_dir)

        if response.returncode != 0:
            error_message = response.stderr.decode("utf-8")
            logging.error(error_message)
        else:
            logging.debug(f"Pulled component '{component_name}' successfully.")

    def __execute_diff(self, file1, file2):
        response = subprocess.run(["diff", file1, file2], capture_output=True)
        return response.stdout.decode()
