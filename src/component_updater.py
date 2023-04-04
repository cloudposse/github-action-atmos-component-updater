import os
import logging
import fnmatch
from typing import List
from enum import Enum
from github.PullRequest import PullRequest
import tools
from utils import io
from atmos_component import AtmosComponent, COMPONENT_YAML
from github_provider import GitHubProvider

COMMIT_MESSAGE_TEMPLATE = "Updated component '{component_name}' to version '{component_version}'"
MAX_NUMBER_OF_DIFF_TO_SHOW = 2


class ComponentUpdaterError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(message)


class ComponentUpdaterResponseState(Enum):
    UNDEFINED = 1
    UPDATED = 2
    NO_VERSION_FOUND_IN_SOURCE_YAML = 3
    NOT_VALID_URI_FOUND_IN_SOURCE_YAML = 4
    URI_IS_NOT_GIT_REPO = 5
    NO_LATEST_TAG_FOUND_IN_COMPONENT_REPO = 6
    ALREADY_UP_TO_DATE = 7
    REMOTE_BRANCH_FOR_COMPONENT_UPDATER_ALREADY_EXIST = 8
    NO_CHANGES_FOUND = 9


class ComponentUpdaterResponse:
    def __init__(self, component: AtmosComponent):
        self.component = component
        self.state: ComponentUpdaterResponseState = ComponentUpdaterResponseState.UNDEFINED
        self.component_path: str
        self.branch_name: str
        self.pull_request: PullRequest


class ComponentUpdater:
    def __init__(self,
                 github_provider: GitHubProvider,
                 infra_repo_dir: str,
                 infra_terraform_dir: str,
                 includes: str,
                 excludes: str,
                 go_getter_tool: str,
                 skip_component_vendoring: bool,
                 max_number_of_prs: int,
                 components_download_dir: str = io.create_tmp_dir(),
                 skip_component_repo_fetching: bool = False):
        self.__github_provider = github_provider
        self.__infra_repo_dir = infra_repo_dir
        self.__infra_terraform_dir = infra_terraform_dir
        self.__download_dir = components_download_dir
        self.__go_getter_tool = go_getter_tool
        self.__skip_component_vendoring = skip_component_vendoring
        self.__max_number_of_prs = min(max_number_of_prs, 10)
        self.__skip_component_repo_fetching = skip_component_repo_fetching
        self.__includes = self.__parse_csv(includes)
        self.__excludes = self.__parse_csv(excludes)

    def update(self) -> List[ComponentUpdaterResponse]:
        infra_components_dir = os.path.join(self.__infra_repo_dir, self.__infra_terraform_dir)

        logging.debug(f"Looking for components in: {infra_components_dir}")

        component_files = self.__get_components(infra_components_dir)

        logging.info(f"Found {len(component_files)} components")

        responses = []

        num_pr_created = 0

        for component_file in component_files:
            response = self.__update_component(component_file)
            responses.append(response)

            num_pr_created += 1 if hasattr(response, 'pull_request') and response.pull_request else 0

            if num_pr_created >= self.__max_number_of_prs:
                logging.info(f"Max number of PRs ({self.__max_number_of_prs}) reached. Skipping the rest")
                break

        return responses

    def __get_components(self, infra_components_dir: str) -> List[str]:
        component_yaml_paths = []

        try:
            for root, _, files in os.walk(infra_components_dir):
                for file in files:
                    if file == COMPONENT_YAML:
                        component_name = os.path.relpath(root, infra_components_dir)

                        if not self.__should_component_be_processed(component_name):
                            continue

                        component_yaml_paths.append(os.path.join(root, file))
        except FileNotFoundError as error:
            logging.error(f"Could not get components from '{infra_components_dir}': {error}")
            raise ComponentUpdaterError(f"Could not get components from '{infra_components_dir}'")

        return component_yaml_paths

    def __update_component(self, component_file: str) -> ComponentUpdaterResponse:
        original_component = AtmosComponent(self.__infra_repo_dir, self.__infra_terraform_dir, component_file)
        response = ComponentUpdaterResponse(original_component)

        logging.info(f"Processing component: {original_component.name}")

        if not self.__component_has_version(original_component):
            logging.warning("Component doesn't have 'version' specified. Skipping")
            response.state = ComponentUpdaterResponseState.NO_VERSION_FOUND_IN_SOURCE_YAML
            return response

        if not self.__component_has_valid_uri(original_component):
            logging.warning("Component doesn't have valid 'uri' specified. Skipping")
            response.state = ComponentUpdaterResponseState.NOT_VALID_URI_FOUND_IN_SOURCE_YAML
            return response

        repo_dir = self.__fetch_component_repo(original_component) if not self.__skip_component_repo_fetching else self.__download_dir

        if not self.__is_git_repo(repo_dir):
            logging.warning("Component repository is not git repo. Can't figure out latest version. Skipping")
            response.state = ComponentUpdaterResponseState.URI_IS_NOT_GIT_REPO
            return response

        latest_tag = tools.git_get_latest_tag(repo_dir)

        if not latest_tag:
            logging.warning("Unable to figure out latest tag. Skipping")
            response.state = ComponentUpdaterResponseState.NO_LATEST_TAG_FOUND_IN_COMPONENT_REPO
            return response

        if original_component.version == latest_tag:
            logging.info("Component already updated. Skipping")
            response.state = ComponentUpdaterResponseState.ALREADY_UP_TO_DATE
            return response

        updated_component = self.__clone_infra_for_component(original_component)

        response.component = updated_component

        branch_name = self.__github_provider.build_component_branch_name(updated_component.normalized_name, latest_tag)

        response.branch_name = branch_name

        if self.__github_provider.branch_exists(updated_component.infra_repo_dir, branch_name):
            logging.info(f"Branch '{branch_name}' already exists. Skipping")
            response.state = ComponentUpdaterResponseState.REMOTE_BRANCH_FOR_COMPONENT_UPDATER_ALREADY_EXIST
            return response

        updated_component.update_version(latest_tag)
        updated_component.persist()

        if not self.__is_vendored(updated_component):
            logging.info(f"Component was not vendored. Updating to version {latest_tag} and do vendoring ...")

            if not self.__skip_component_vendoring:
                try:
                    tools.atmos_vendor_component(updated_component)
                except tools.ToolExecutionError as error:
                    logging.error(f"Failed to vendor component: {error}")
                    return response

            pull_request: PullRequest = self.__create_branch_and_pr(updated_component.infra_repo_dir, original_component, updated_component, branch_name)
            response.pull_request = pull_request
            response.state = ComponentUpdaterResponseState.UPDATED
            return response

        # re-vendor component
        try:
            tools.atmos_vendor_component(updated_component)
        except tools.ToolExecutionError as error:
            logging.error(f"Failed to vendor component: {error}")
            return response

        if self.__does_component_needs_to_be_updated(original_component, updated_component):
            pull_request: PullRequest = self.__create_branch_and_pr(updated_component.infra_repo_dir, original_component, updated_component, branch_name)
            response.pull_request = pull_request
            response.state = ComponentUpdaterResponseState.UPDATED
            return response

        logging.info("Looking good. No changes found")
        response.state = ComponentUpdaterResponseState.NO_CHANGES_FOUND
        return response

    def __fetch_component_repo(self, component: AtmosComponent):
        normalized_repo_path = component.uri_repo.replace('/', '-') if component.uri_repo else ''
        tools.go_getter_pull_component_repo(self.__go_getter_tool, component, normalized_repo_path, self.__download_dir)
        return os.path.join(self.__download_dir, normalized_repo_path)

    def __is_git_repo(self, repo_dir: str) -> bool:
        return os.path.exists(os.path.join(repo_dir, '.git'))

    def __is_vendored(self, component: AtmosComponent) -> bool:
        updated_component_files = io.get_filenames_in_dir(component.component_dir, ['**/*'])
        return len(updated_component_files) > 1

    def __clone_infra_for_component(self, component: AtmosComponent):
        update_infra_repo_dir = io.create_tmp_dir()
        io.copy_dirs(self.__infra_repo_dir, update_infra_repo_dir)
        component_file = os.path.join(update_infra_repo_dir, component.relative_path)
        return AtmosComponent(update_infra_repo_dir, self.__infra_terraform_dir, component_file)

    def __does_component_needs_to_be_updated(self, original_component: AtmosComponent, updated_component: AtmosComponent) -> bool:
        updated_files = io.get_filenames_in_dir(updated_component.component_dir, ['**/*'])

        needs_update = False
        num_diffs = 0

        for updated_file in updated_files:
            # skip "component.yaml"
            if updated_file.endswith(COMPONENT_YAML):
                continue

            relative_path = os.path.relpath(updated_file, updated_component.infra_repo_dir)
            original_file = os.path.join(original_component.infra_repo_dir, relative_path)

            if not os.path.isfile(original_file):
                logging.info(f"New file: {relative_path}")
                needs_update = True
                continue

            if io.calc_file_md5_hash(original_file) != io.calc_file_md5_hash(updated_file):
                logging.info(f"File changed: {relative_path}")
                if num_diffs < MAX_NUMBER_OF_DIFF_TO_SHOW:
                    logging.info(f"diff: {tools.diff(original_file, updated_file)}")
                    num_diffs += 1
                needs_update = True

        return needs_update

    def __create_branch_and_pr(self, repo_dir, original_component: AtmosComponent, updated_component: AtmosComponent, branch_name: str) -> PullRequest:
        self.__github_provider.create_branch_and_push_all_changes(repo_dir,
                                                                  branch_name,
                                                                  COMMIT_MESSAGE_TEMPLATE.format(
                                                                      component_name=updated_component.name,
                                                                      component_version=updated_component.version))

        logging.info(f"Created branch: {branch_name} in 'origin'")

        logging.info(f"Opening PR for branch {branch_name}")

        pull_request: PullRequest = self.__github_provider.open_pr(branch_name,
                                                                   original_component,
                                                                   updated_component)

        logging.info(f"Opened PR #{pull_request.number}")

        opened_prs = self.__github_provider.get_open_prs_for_component(updated_component.normalized_name)

        for opened_pr in opened_prs:
            if opened_pr.number != pull_request.number:
                closing_message = f"Closing in favor of PR #{pull_request.number}"
                self.__github_provider.close_pr(opened_pr, closing_message)
                logging.info(f"Closed pr {opened_pr.number} in favor of #{pull_request.number}")

        return pull_request

    def __component_has_version(self, component) -> bool:
        return bool(component.version)

    def __component_has_valid_uri(self, component) -> bool:
        return bool(component.uri_repo and component.uri_path)

    def __parse_csv(self, csv_list: str) -> List[str]:
        return [x.strip() for x in csv_list.split(',')] if csv_list else []

    def __should_component_be_processed(self, component_name: str) -> bool:
        if len(self.__includes) == 0 and len(self.__excludes) == 0:
            return True

        should_be_processed = False

        if self.__includes:
            for include_pattern in self.__includes:
                if fnmatch.fnmatch(component_name, include_pattern):
                    should_be_processed = True
                    break

        if self.__excludes:
            for exclude_pattern in self.__excludes:
                if fnmatch.fnmatch(component_name, exclude_pattern):
                    should_be_processed = False
                    break

        return should_be_processed
