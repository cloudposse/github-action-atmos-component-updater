import logging
import os
from utils import io
from utils import tools
from atmos_component import AtmosComponent, COMPONENT_YAML
from github_provider import GitHubProvider
from git_provider import GitProvider

TERRAFORM_COMPONENTS_SUBDIR = 'components/terraform'
COMMIT_MESSAGE_TEMPLATE = "Updated component '{component_name}' to version '{component_version}'"


class ComponentUpdaterError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(message)


class ComponentUpdater:
    def __init__(self, github_provider: GitHubProvider, infra_repo_dir: str):
        self.__github_provider = github_provider
        self.__infra_repo_dir = infra_repo_dir
        self.__download_dir = io.create_tmp_dir()

    def update(self):
        infra_components_dir = os.path.join(self.__infra_repo_dir, TERRAFORM_COMPONENTS_SUBDIR)

        logging.info(f"Looking for components in this directory: {infra_components_dir}")

        component_files = self.__get_components(infra_components_dir)

        logging.info(f"Found {len(component_files)} components")

        for component_file in component_files:
            self.__update_component(component_file)

    def __get_components(self, infra_components_dir):
        paths = []

        try:
            for root, dirs, files in os.walk(infra_components_dir):
                for file in files:
                    if file == COMPONENT_YAML:
                        paths.append(os.path.join(root, file))
        except FileNotFoundError:
            raise ComponentUpdaterError(
                f"Could not find components in '{infra_components_dir}'. Directory doesn't exist.")

        return paths

    def __update_component(self, component_file: str):
        original_component = AtmosComponent(self.__infra_repo_dir, component_file)

        logging.info(f"Processing component: {original_component.get_name()}")

        if not original_component.get_version():
            logging.info(f"Component doesn't have version specified. Skipping.")
            return

        normalized_repo_path: str = original_component.get_component_uri_repo().replace('/', '-')
        tools.go_getter(original_component, normalized_repo_path)
        repo_dir = os.path.join(self.__download_dir, normalized_repo_path)

        if not os.path.exists(os.path.join(repo_dir, '.git')):
            logging.info(f"Component repository is not .git repo. Can't figure out latest version. Skipping")
            return

        try:
            latest_tag = tools.git_describe_tag(repo_dir)
        except tools.ToolExecutionError as e:
            logging.warning("No tags in components repo. Can not figure out latest version. Skipping")
            return

        if original_component.get_version() == latest_tag:
            logging.info(f"Component already updated: {original_component.get_name()}")
            return

        updated_component = self.__clone_infra_for_component(original_component)

        if self.__is_not_vendored(updated_component):
            logging.debug(f"Component was not vendored: {original_component.get_name()}")
            updated_component.update_version(latest_tag)
            updated_component.persist()
            self.__create_pr(original_component, updated_component, latest_tag)
            return

        vendored_component = self.__clone_infra_for_component(original_component)
        vendored_component.update_version(latest_tag)
        io.remove_all_from_dir(vendored_component.get_component_dir())
        vendored_component.persist()

        tools.atmos_vendor_pull(vendored_component.get_infra_repo_dir(), vendored_component.get_name())

        vendored_component_files = io.get_filenames_in_dir(vendored_component.get_component_dir(), ['**/*'])

        updatable = True

        for vendored_file in vendored_component_files:
            # skip "component.yaml" or ends with .md
            if vendored_file.endswith(COMPONENT_YAML) or vendored_file.endswith('.md'):
                continue

            relative_path = os.path.relpath(vendored_file, vendored_component.get_infra_repo_dir())
            original_file = os.path.join(updated_component.get_infra_repo_dir(), relative_path)

            if not os.path.isfile(original_file):
                logging.warning(f"File doesn't exist: {relative_path}")
                updatable = False
                break

            if io.calc_file_md5_hash(original_file) != io.calc_file_md5_hash(vendored_file):
                logging.warning(f"File has changed: {relative_path}")
                logging.debug(f"diff: " + tools.diff(original_file, vendored_file))
                updatable = False
                break

        if updatable:
            updated_component.update_version(latest_tag)
            updated_component.persist()
            self.__create_pr(original_component, updated_component, latest_tag)
        else:
            logging.warning(f"Component can not be updated: {updated_component.get_name()}")

    def __is_not_vendored(self, component: AtmosComponent):
        updated_component_files = io.get_filenames_in_dir(component.get_component_dir(), ['**/*'])
        return len(updated_component_files) == 1 and updated_component_files[0].endswith(COMPONENT_YAML)

    def __clone_infra_for_component(self, component):
        update_infra_repo_dir = io.create_tmp_dir()
        logging.debug(f"Infra repo dir: {update_infra_repo_dir}")
        io.copy_dirs(self.__infra_repo_dir, update_infra_repo_dir)
        component_file = os.path.join(update_infra_repo_dir, component.get_relative_path())
        return AtmosComponent(update_infra_repo_dir, component_file)

    def __create_pr(self, original_component, updated_component, latest_tag):
        git_provider = GitProvider(updated_component.get_infra_repo_dir())
        branch_name = git_provider.get_component_branch_name(updated_component.get_name(), latest_tag)
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
                                            original_component,
                                            updated_component)
        logging.info(f"Opened PR #{pr.number}")

        opened_prs = self.__github_provider.get_open_prs_for_component(updated_component.get_name())

        for opened_pr in opened_prs:
            if opened_pr.number != pr.number:
                closing_message = f"Closing in favor of PR #{pr.number}"
                self.__github_provider.close_pr(opened_pr, closing_message)
                logging.info(f"Closed pr {opened_pr.number} in favor of #{pr.number}")
