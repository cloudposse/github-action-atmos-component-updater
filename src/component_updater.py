import copy
import os
import sys
import logging
import fnmatch
from typing import List, Optional
from enum import Enum
from tools_manager import ToolsManager, ToolExecutionError
from utils import io
from atmos_component import AtmosComponent, COMPONENT_YAML, README_EXTENTION
from github_provider import GitHubProvider, PullRequestCreationResponse
from config import Config


COMMIT_MESSAGE_TEMPLATE = "Updated component '{component_name}' to version '{component_version}'"
MAX_NUMBER_OF_DIFF_TO_SHOW = 3


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
    REMOTE_BRANCH_FOR_COMPONENT_UPDATER_ALREADY_EXISTS = 8
    NO_CHANGES_FOUND = 9
    FAILED_TO_VENDOR_COMPONENT = 10
    MAX_PRS_REACHED = 11
    PR_FOR_BRANCH_ALREADY_EXISTS = 12
    COMPONENT_VENDORED_BUT_VENDORING_DISABLED = 13


class ComponentUpdaterResponse:
    def __init__(self, component: AtmosComponent):
        self.component = component
        self.state: ComponentUpdaterResponseState = ComponentUpdaterResponseState.UNDEFINED
        self.component_path: str
        self.branch_name: str
        self.pull_request_creation_response: Optional[PullRequestCreationResponse] = None


class ComponentUpdater:
    def __init__(self,
                 github_provider: GitHubProvider,
                 tools_manager: ToolsManager,
                 infra_terraform_dirs: List[str],
                 config: Config):
        self.__github_provider = github_provider
        self.__infra_terraform_dirs = infra_terraform_dirs
        self.__config = config
        self.__tools_manager = tools_manager
        self.__num_pr_created = 0

    def update(self) -> List[ComponentUpdaterResponse]:
        responses = []

        for infra_terraform_dir in self.__infra_terraform_dirs:
            responses.extend(self.__update_terraform_dir(infra_terraform_dir))

        return responses

    def __update_terraform_dir(self, infra_terraform_dir) -> List[ComponentUpdaterResponse]:
        responses = []

        infra_components_dir = os.path.join(self.__config.infra_repo_dir, infra_terraform_dir)

        logging.debug(f"Looking for components in: {infra_components_dir}")

        component_files = self.__get_components(infra_components_dir)

        logging.info(f"Found {len(component_files)} components")

        affected = []

        try:
            for component_file in component_files:
                response = self.__update_component(infra_terraform_dir, component_file)
                logging.debug(f"Response state after component update: {response.state.name}")
                responses.append(response)

                if response.state == ComponentUpdaterResponseState.UPDATED:
                    affected.append(response.component.name)
        except (ComponentUpdaterError, ToolExecutionError) as error:
            logging.error(error.message)
            sys.exit(1)
        finally:
            io.serialize_to_json_file(self.__config.affected_components_file, affected)

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

        return sorted(component_yaml_paths)

    def __is_vendored(self, component: AtmosComponent, vendored_component: AtmosComponent) -> bool:
        """Checks if component has subset of files that vendored component does. This way we will be able to detect if component was pulled or not"""
        component_files = set([os.path.relpath(f, component.component_dir) for f in io.get_filenames_in_dir(component.component_dir, ['**/*'])])
        vendored_component_files = set([os.path.relpath(f, vendored_component.component_dir) for f in io.get_filenames_in_dir(vendored_component.component_dir, ['**/*'])])
        return vendored_component_files.issubset(component_files)

    def __update_component(self, infra_terraform_dir, component_file: str) -> ComponentUpdaterResponse:
        original_component = AtmosComponent(self.__config.infra_repo_dir, infra_terraform_dir, component_file)
        response = ComponentUpdaterResponse(original_component)

        if self.__num_pr_created >= self.__config.max_number_of_prs:
            logging.info(f"Max number of PRs ({self.__config.max_number_of_prs}) reached. Skipping component update for '{original_component.name}'")
            response.state = ComponentUpdaterResponseState.MAX_PRS_REACHED
            return ComponentUpdaterResponse(original_component)

        logging.info(f"Processing component: {original_component.name}")
        logging.debug(f"Original component:\n{str(original_component)}")

        if not original_component.has_version():
            logging.error(f"Component '{original_component.name}' doesn't have 'version' specified. Skipping")
            response.state = ComponentUpdaterResponseState.NO_VERSION_FOUND_IN_SOURCE_YAML
            return response

        if not original_component.has_valid_uri():
            logging.error(f"Component '{original_component.name}' doesn't have valid 'uri' specified. Skipping")
            response.state = ComponentUpdaterResponseState.NOT_VALID_URI_FOUND_IN_SOURCE_YAML
            return response

        migrated_component = copy.deepcopy(original_component)
        migrated_component.migrate()

        repo_dir = self.__fetch_component_repo(migrated_component) if not self.__config.skip_component_repo_fetching else self.__config.components_download_dir

        if not self.__tools_manager.is_git_repo(repo_dir):
            logging.error(f"Component '{original_component.name}' uri is not git repo. Can't figure out latest version. Skipping")
            response.state = ComponentUpdaterResponseState.URI_IS_NOT_GIT_REPO
            return response

        latest_tag = self.__tools_manager.git_get_latest_tag(repo_dir)
        logging.info(f"Latest tag for component '{original_component.name}' is '{latest_tag}'")

        if not latest_tag:
            logging.error(f"Unable to figure out latest tag for component '{original_component.name}' source uri. Skipping")
            response.state = ComponentUpdaterResponseState.NO_LATEST_TAG_FOUND_IN_COMPONENT_REPO
            return response

        if original_component.version == latest_tag:
            logging.info(f"Component '{original_component.name}' already updated. Skipping")
            response.state = ComponentUpdaterResponseState.ALREADY_UP_TO_DATE
            return response

        updated_component = self.__clone_infra_for_component(infra_terraform_dir, migrated_component)
        updated_component.migrate()

        logging.debug(f"Updated component:\n{str(updated_component)}")

        response.component = updated_component

        branch_name = self.__github_provider.build_component_branch_name(updated_component.normalized_name, latest_tag)

        response.branch_name = branch_name

        if self.__github_provider.branch_exists(branch_name):
            logging.warning(f"Branch '{branch_name}' already exists. Skipping")
            response.state = ComponentUpdaterResponseState.REMOTE_BRANCH_FOR_COMPONENT_UPDATER_ALREADY_EXISTS
            return response

        if self.__github_provider.pr_for_branch_exists(branch_name):
            logging.warning(f"PR for branch '{branch_name}' already exists. Skipping")
            response.state = ComponentUpdaterResponseState.PR_FOR_BRANCH_ALREADY_EXISTS
            return response

        updated_component.update_version(latest_tag)
        updated_component.persist()

        original_vendored_component: AtmosComponent = self.__clone_infra_for_component(infra_terraform_dir, original_component)
        updated_vendored_component: AtmosComponent = self.__clone_infra_for_component(infra_terraform_dir, updated_component)

        logging.debug(f"Original re-vendored component:\n{str(original_vendored_component)}")
        logging.debug(f"Updated re-vendored component:\n{str(updated_vendored_component)}")

        try:
            self.__tools_manager.atmos_vendor_component(original_vendored_component)
            self.__tools_manager.atmos_vendor_component(updated_vendored_component)
        except ToolExecutionError as error:
            logging.error(f"Failed to vendor component: {error}")
            response.state = ComponentUpdaterResponseState.FAILED_TO_VENDOR_COMPONENT
            return response

        # - vendoring_enabled = true
        #   - component vendored     => do vendor
        #   - component not vendored => do vendor
        # - vendoring_enabled = false
        #   - component vendored     => skip component
        #   - component not vendored => do not vendor
        needs_update, files_to_update, files_to_remove = self.__does_component_needs_to_be_updated(original_vendored_component, updated_vendored_component, original_component)
        if needs_update:
            if self.__config.vendoring_enabled:
                self.__tools_manager.atmos_vendor_component(updated_component)
            else:
                if self.__is_vendored(original_component, original_vendored_component):
                    logging.error(f"Component '{original_component.name}' is vendored but vendoring disabled. Skipping")
                    response.state = ComponentUpdaterResponseState.COMPONENT_VENDORED_BUT_VENDORING_DISABLED
                    return response

            pull_request_creation_response: PullRequestCreationResponse = self.__create_branch_and_pr(updated_component.infra_repo_dir,
                                                                                                      files_to_update,
                                                                                                      files_to_remove,
                                                                                                      original_component,
                                                                                                      updated_component,
                                                                                                      branch_name)
            response.pull_request_creation_response = pull_request_creation_response

            response.state = ComponentUpdaterResponseState.UPDATED

            if self.__config.dry_run or (response.pull_request_creation_response and response.pull_request_creation_response.pull_request):
                self.__num_pr_created += 1

            return response
        else:
            logging.info("Looking good. No changes found")
            response.state = ComponentUpdaterResponseState.NO_CHANGES_FOUND
            return response

    def __fetch_component_repo(self, component: AtmosComponent):
        normalized_repo_path = component.uri_repo.replace('/', '-') if component.uri_repo else ''
        self.__tools_manager.go_getter_pull_component_repo(component, normalized_repo_path, self.__config.components_download_dir)
        return os.path.join(self.__config.components_download_dir, normalized_repo_path)

    def __clone_infra_for_component(self, infra_terraform_dir: str, component: AtmosComponent):
        update_infra_repo_dir = io.create_tmp_dir()
        io.copy_dirs(component.infra_repo_dir, update_infra_repo_dir)
        component_file = os.path.join(update_infra_repo_dir, component.relative_path)
        return AtmosComponent(update_infra_repo_dir, infra_terraform_dir, component_file)

    def __does_component_needs_to_be_updated(self, original_component: AtmosComponent, updated_component: AtmosComponent, original_component_source: AtmosComponent) -> (bool, List[str], List[str]):
        updated_files = io.get_filenames_in_dir(updated_component.component_dir, ['**/*'])
        original_files = io.get_filenames_in_dir(original_component.component_dir, ['**/*'])

        logging.debug(f"Original files: {original_files}")
        logging.debug(f"Updated files: {updated_files}")

        needs_update = False
        num_diffs = 0

        files_to_update = []
        files_to_remove = []

        for updated_file in updated_files:
            # skip "component.yaml"
            if updated_file.endswith(COMPONENT_YAML):
                continue

            # skip folders
            if not os.path.isfile(updated_file):
                continue

            relative_path = os.path.relpath(updated_file, updated_component.infra_repo_dir)
            original_file = os.path.join(original_component.infra_repo_dir, relative_path)

            files_to_update.append(relative_path)
            if not os.path.isfile(original_file):
                logging.info(f"New file: {relative_path}")
                # Adding *.md file does not require component update, but still should be included into a PR
                needs_update = needs_update or not relative_path.endswith(README_EXTENTION)
                continue

            if io.calc_file_md5_hash(original_file) != io.calc_file_md5_hash(updated_file):
                logging.info(f"File changed: {relative_path}")
                if num_diffs < MAX_NUMBER_OF_DIFF_TO_SHOW:
                    logging.info(f"diff: {self.__tools_manager.diff(original_file, updated_file)}")
                    num_diffs += 1
                # Adding *.md file does not require component update, but still should be included into a PR
                needs_update = needs_update or not relative_path.endswith(README_EXTENTION)

        for original_file in original_files:
            relative_path = os.path.relpath(original_file, original_component.infra_repo_dir)
            updated_file = os.path.join(updated_component.infra_repo_dir, relative_path)
            source_file = os.path.join(original_component_source.infra_repo_dir, relative_path)

            if os.path.isfile(source_file) and not os.path.isfile(updated_file):
                logging.info(f"Remove file: {relative_path}")
                files_to_remove.append(relative_path)
                # Adding *.md file does not require component update, but still should be included into a PR
                needs_update = needs_update or not relative_path.endswith(README_EXTENTION)
                continue

        if needs_update:
            logging.info(f"Component '{os.path.relpath(original_component.component_file, original_component.infra_repo_dir)}' needs to be updated")
            files_to_update.append(os.path.relpath(original_component.component_file, original_component.infra_repo_dir))

        return (needs_update, files_to_update, files_to_remove)

    def __create_branch_and_pr(self, repo_dir, files_to_update, files_to_remove, original_component: AtmosComponent, updated_component: AtmosComponent, branch_name: str) -> PullRequestCreationResponse:
        self.__github_provider.create_branch_and_push_all_changes(repo_dir,
                                                                  files_to_update,
                                                                  files_to_remove,
                                                                  branch_name,
                                                                  COMMIT_MESSAGE_TEMPLATE.format(
                                                                      component_name=updated_component.name,
                                                                      component_version=updated_component.version))

        logging.info(f"Created branch: {branch_name} in 'origin'")
        logging.info(f"Opening PR for branch {branch_name}")

        pull_request_creation_response: PullRequestCreationResponse = self.__github_provider.open_pr(repo_dir,
                                                                                                     branch_name,
                                                                                                     original_component,
                                                                                                     updated_component)
        if not self.__config.dry_run and pull_request_creation_response.pull_request:
            pull_request = pull_request_creation_response.pull_request

            logging.info(f"Opened PR #{pull_request.number}")

            opened_prs = self.__github_provider.get_open_prs_for_component(updated_component.normalized_name)

            for opened_pr in opened_prs:
                if opened_pr.number != pull_request.number:
                    closing_message = f"Closing in favor of PR #{pull_request.number}"
                    self.__github_provider.close_pr(opened_pr, closing_message)
                    logging.info(f"Closed pr {opened_pr.number} in favor of #{pull_request.number}")

        return pull_request_creation_response

    def __should_component_be_processed(self, component_name: str) -> bool:
        if len(self.__config.include) == 0 and len(self.__config.exclude) == 0:
            return True

        should_be_processed = False

        if self.__config.include:
            for include_pattern in self.__config.include:
                if fnmatch.fnmatch(component_name, include_pattern):
                    should_be_processed = True
                    break

        if self.__config.exclude:
            for exclude_pattern in self.__config.exclude:
                if fnmatch.fnmatch(component_name, exclude_pattern):
                    should_be_processed = False
                    break

        return should_be_processed
