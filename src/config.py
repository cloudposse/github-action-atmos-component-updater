import os
from typing import List
from utils import io, utils


class Config:
    # pylint: disable=too-many-arguments
    def __init__(self,
                 infra_repo_name: str,
                 infra_repo_dir: str,
                 infra_terraform_dirs: str,
                 skip_component_vendoring: bool,
                 max_number_of_prs: int,
                 include: str,
                 exclude: str,
                 go_getter_tool: str,
                 dry_run: bool,
                 affected_components_file: str = '',
                 pr_title_template: str = '',
                 pr_body_template: str = '',
                 pr_labels: str = 'component-update'):
        self.infra_repo_name: str = infra_repo_name
        self.infra_repo_dir: str = infra_repo_dir
        self.infra_terraform_dirs: List[str] = utils.parse_comma_or_new_line_separated_list(infra_terraform_dirs)
        self.skip_component_vendoring: bool = skip_component_vendoring
        self.max_number_of_prs: int = max_number_of_prs
        self.include: List[str] = utils.parse_comma_or_new_line_separated_list(include)
        self.exclude: List[str] = utils.parse_comma_or_new_line_separated_list(exclude)
        self.go_getter_tool: str = go_getter_tool
        self.dry_run: bool = dry_run
        self.components_download_dir: str = io.create_tmp_dir()
        self.skip_component_repo_fetching: bool = False
        self.pr_title_template: str = pr_title_template
        self.pr_body_template: str = pr_body_template
        self.pr_labels: List[str] = utils.parse_comma_or_new_line_separated_list(pr_labels)

        if affected_components_file:
            self.affected_components_file = affected_components_file
        else:
            tmp_dir = io.create_tmp_dir()
            self.affected_components_file = os.path.join(tmp_dir, 'affected_components.json')

    def __repr__(self):
        attributes = "\n".join(f"- {key}={value!r}" for key, value in vars(self).items())
        return f"{self.__class__.__name__}({attributes})"
