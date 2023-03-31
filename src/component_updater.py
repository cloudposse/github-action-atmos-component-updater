import logging
import os
from utils import io
from utils import tools
from atmos_component import AtmosComponent, COMPONENT_YAML
from github_provider import GitHubProvider
from git_provider import GitProvider

TERRAFORM_COMPONENTS_SUBDIR = 'components/terraform'
COMMIT_MESSAGE_TEMPLATE = "Updated component '{component_name}' to version '{component_version}'"
MAX_NUMBER_OF_DIFF_TO_SHOW = 3


class ComponentUpdaterError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(message)


class ComponentUpdater:
    def __init__(self, github_provider: GitHubProvider, infra_repo_dir: str, go_getter_tool: str):
        self.__github_provider = github_provider
        self.__infra_repo_dir = infra_repo_dir
        self.__download_dir = io.create_tmp_dir()
        self.__go_getter_tool = go_getter_tool

    def update(self):
        infra_components_dir = os.path.join(self.__infra_repo_dir, TERRAFORM_COMPONENTS_SUBDIR)

        logging.debug(f"Looking for components in: {infra_components_dir}")

        component_files = self.__get_components(infra_components_dir)

        logging.info(f"Found {len(component_files)} components")

        for component_file in component_files:
            self.__update_component(component_file)

    def __get_components(self, infra_components_dir):
        component_yaml_paths = []

        try:
            for root, dirs, files in os.walk(infra_components_dir):
                for file in files:
                    if file == COMPONENT_YAML:
                        component_yaml_paths.append(os.path.join(root, file))
        except FileNotFoundError:
            raise ComponentUpdaterError(f"Could not get components from '{infra_components_dir}'")

        return component_yaml_paths

    def __update_component(self, component_file: str):
        original_component = AtmosComponent(self.__infra_repo_dir, component_file)

        logging.info(f"Processing component: {original_component.get_name()}")

        if not original_component.has_version():
            logging.warning(f"Component doesn't have 'version' specified. Skipping")
            return

        if not original_component.has_valid_uri():
            logging.warning(f"Component doesn't have valid 'uri' specified. Skipping")
            return

        repo_dir = self.__fetch_component_repo(original_component)

        if not self.__is_git_repo():
            logging.warning(f"Component repository is not git repo. Can't figure out latest version. Skipping")
            return

        latest_tag = tools.git_get_latest_tag(repo_dir)

        if not latest_tag:
            logging.warning("Unable to figure out latest tag. Skipping")
            return

        if original_component.get_version() == latest_tag:
            logging.info(f"Component already updated. Skipping")
            return

        updated_component = self.__clone_infra_for_component(original_component)
        updated_component.update_version(latest_tag)
        updated_component.persist()

        if not self.__is_vendored(updated_component):
            logging.info(f"Component was not vendored. Updating to version {latest_tag} and do vendoring ...")
            tools.atmos_vendor_component(updated_component.get_infra_repo_dir(), updated_component.get_name())
            self.__create_branch_and_pr(original_component, updated_component, latest_tag)
            return

        vendored_component = self.__clone_infra_for_component(original_component)
        vendored_component.update_version(latest_tag)
        vendored_component.persist()
        tools.atmos_vendor_pull(vendored_component.get_infra_repo_dir(), vendored_component.get_name())

        if self.__does_component_needs_to_be_updated(original_component, vendored_component):
            self.__create_branch_and_pr(original_component, updated_component, latest_tag)
        else:
            logging.info(f"Looking good. No changes found")

    def __fetch_component_repo(self, component: AtmosComponent):
        normalized_repo_path = component.get_component_uri_repo().replace('/', '-')
        tools.go_getter_pull_component_repo(self.__go_getter_tool, component, normalized_repo_path, self.__download_dir)
        return os.path.join(self.__download_dir, normalized_repo_path)

    def __is_git_repo(self, repo_dir: str):
        return os.path.exists(os.path.join(repo_dir, '.git'))

    def __is_vendored(self, component: AtmosComponent):
        updated_component_files = io.get_filenames_in_dir(component.get_component_dir(), ['**/*'])
        return len(updated_component_files) > 1

    def __clone_infra_for_component(self, component: AtmosComponent):
        update_infra_repo_dir = io.create_tmp_dir()
        io.copy_dirs(self.__infra_repo_dir, update_infra_repo_dir)
        component_file = os.path.join(update_infra_repo_dir, component.get_relative_path())
        return AtmosComponent(update_infra_repo_dir, component_file)

    def __does_component_needs_to_be_updated(self, updated_component: AtmosComponent, vendored_component: AtmosComponent):
        vendored_component_files = io.get_filenames_in_dir(vendored_component.get_component_dir(), ['**/*'])

        needs_update = False
        num_diffs = 0

        for vendored_file in vendored_component_files:
            # skip "component.yaml"
            if vendored_file.endswith(COMPONENT_YAML):
                continue

            relative_path = os.path.relpath(vendored_file, vendored_component.get_infra_repo_dir())
            original_file = os.path.join(updated_component.get_infra_repo_dir(), relative_path)

            if not os.path.isfile(original_file):
                logging.info(f"New file: {relative_path}")
                needs_update = True
                continue

            if io.calc_file_md5_hash(original_file) != io.calc_file_md5_hash(vendored_file):
                logging.info(f"File changed: {relative_path}")
                if num_diffs < MAX_NUMBER_OF_DIFF_TO_SHOW:
                    logging.info(f"diff: " + tools.diff(original_file, vendored_file))
                    num_diffs += 1
                needs_update = True

        return needs_update

    def __create_branch_and_pr(self, original_component, updated_component, latest_tag):
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

        logging.info(f"Created branch: {branch_name} in 'origin'")

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
