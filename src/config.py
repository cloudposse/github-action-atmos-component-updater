import os
from utils import io


class Config:
    # pylint: disable=too-many-arguments
    def __init__(self,
                 infra_repo_name: str,
                 infra_repo_dir: str,
                 infra_terraform_dirs: str,
                 skip_component_vendoring: bool,
                 max_number_of_prs: int,
                 includes: str,
                 excludes: str,
                 go_getter_tool: str,
                 dry_run: bool,
                 affected_components_file: str):
        self.infra_repo_name = infra_repo_name
        self.infra_repo_dir = infra_repo_dir
        self.infra_terraform_dirs = infra_terraform_dirs
        self.skip_component_vendoring = skip_component_vendoring
        self.max_number_of_prs = max_number_of_prs
        self.includes = includes
        self.excludes = excludes
        self.go_getter_tool = go_getter_tool
        self.dry_run = dry_run
        self.components_download_dir: str = io.create_tmp_dir()
        self.skip_component_repo_fetching: bool = False

        if affected_components_file:
            self.affected_components_file = affected_components_file
        else:
            tmp_dir = io.create_tmp_dir()
            self.affected_components_file = os.path.join(tmp_dir, 'affected_components.txt')

    # pylint: disable=consider-using-dict-items
    def __str__(self):
        return '\n'.join((f'- {item}: {self.__dict__[item]}' for item in self.__dict__))
