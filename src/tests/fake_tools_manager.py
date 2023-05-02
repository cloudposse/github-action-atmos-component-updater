import os
import shutil
import logging
from tools_manager import ToolsManager, ToolExecutionError
from atmos_component import AtmosComponent


TERRAFORM_COMPONENTS_REPO_PATH = 'src/tests/fixtures/terraform-aws-components'


class FakeToolsManager(ToolsManager):
    # pylint: disable=super-init-not-called
    def __init__(self, latest_tag, is_valid_git_repo: bool = True):
        self.latest_tag = latest_tag
        self.is_valid_git_repo: bool = is_valid_git_repo

    def atmos_vendor_component(self, component: AtmosComponent, is_dry_run: bool = False):
        logging.debug(f"Vendoring component: {component}")

        source_file = os.path.join(os.getcwd(), TERRAFORM_COMPONENTS_REPO_PATH, str(component.version), 'modules', component.name)

        if os.path.exists(source_file):
            shutil.copytree(
                source_file,
                os.path.dirname(component.component_file),
                dirs_exist_ok=True)
        else:
            raise ToolExecutionError(f"Component {component.name} not found in {source_file}")

    def go_getter_pull_component_repo(self, component: AtmosComponent, destination_dir: str, download_dir: str):
        logging.debug(f"Fake pulling component repo with go_getter: {component.name}")

    def git_get_latest_tag(self, git_dir: str):
        return self.latest_tag

    def is_git_repo(self, repo_dir: str) -> bool:
        return self.is_valid_git_repo
