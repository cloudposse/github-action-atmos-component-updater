import re
import logging
import os
import base64
from typing import Optional, Tuple, List
import jinja2
import git.repo
from github import Github, InputGitTreeElement
from github.PullRequest import PullRequest
from jinja2 import FileSystemLoader, Template
from atmos_component import AtmosComponent
from config import Config


BRANCH_PREFIX = 'component-update'
TEMPLATES_DIR = 'src/templates'
DEFAULT_PR_TITLE_TEMPLATE = 'pr_title.j2.md'
DEFAULT_PR_BODY_TEMPLATE = 'pr_body.j2.md'


class PullRequestCreationResponse:
    def __init__(self,
                 branch: str,
                 title: str,
                 body: str,
                 labels: List[str],
                 pull_request: Optional[PullRequest] = None):
        self.branch: str = branch
        self.title: str = title
        self.body: str = body
        self.labels: List[str] = labels
        self.pull_request: Optional[PullRequest] = pull_request

    def __repr__(self):
        attributes = "\n".join(f"- {key}={value!r}" for key, value in vars(self).items())
        return f"{self.__class__.__name__}({attributes})"


class GitHubProvider:
    def __init__(self, config: Config, github: Github):
        self.__config = config
        self.__github = github
        self.__repo = self.__github.get_repo(config.infra_repo_name)
        self.__branches = self.get_branches(config.infra_repo_dir)
        self.__branch_to_pr_map = self.build_branch_to_pr_map()
        self.__pull_requests = None
        self.__pr_title_template = self.__load_template(self.__config.pr_title_template, DEFAULT_PR_TITLE_TEMPLATE)
        self.__pr_body_template = self.__load_template(self.__config.pr_body_template, DEFAULT_PR_BODY_TEMPLATE)

    def build_component_branch_name(self, component_name: str, tag: str):
        normalized_component_name: str = re.sub(r'[^a-zA-Z0-9-_]+', '', component_name)
        return f'{BRANCH_PREFIX}/{normalized_component_name}/{tag}'

    def build_branch_to_pr_map(self):
        branch_to_pr_map = {}

        for pull_request in self.__repo.get_pulls(state='all'):
            logging.debug(f"Found PR: '{pull_request.title}' for branch '{pull_request.head.ref}'")
            branch_to_pr_map[pull_request.head.ref] = pull_request

        return branch_to_pr_map

    def pr_for_branch_exists(self, branch_name: str):
        logging.info(f"Looking for PR with branch: {branch_name}")
        return branch_name in self.__branch_to_pr_map

    def get_branches(self, repo_dir: str):
        branches = []

        try:
            repo = git.repo.Repo(repo_dir)

            for branch in repo.heads:
                logging.debug(f"Found branch: {branch.name}")
                branches.append(branch.name)

            remote_branches = repo.remote().refs

            for branch in remote_branches:
                logging.debug(f"Found branch: {branch.name}")
                branches.append(branch.name)
        except Exception as exception:  # pylint: disable=broad-exception-caught
            logging.error(str(exception))

        return set(branches)

    def create_branch_and_push_all_changes(self, repo_dir, files_to_update, files_to_remove, branch_name: str, commit_message: str):
        repo = git.repo.Repo(repo_dir)

        base_branch = self.__repo.get_branch(repo.active_branch.name)
        base_tree = self.__repo.get_git_tree(base_branch.commit.sha)

        parent_commit = self.__repo.get_git_commit(base_branch.commit.sha)

        if self.__config.dry_run:
            logging.info(f"Dry run: Changes pushed to branch {branch_name}")
            return

        repo.git.add(A=True)

        tree_elements = []

        for key, value in repo.index.entries.items():
            if value.path not in files_to_update:
                continue

            file_path = os.path.join(repo_dir, value.path)
            if os.path.getsize(file_path) > 100000000:
                raise Exception("File size limit reached! File '{}' is larger than 100MB.".format(value.path))

            with open(file_path, "rb") as f:
                data = base64.b64encode(f.read())
                blob = self.__repo.create_git_blob(content=data.decode("utf-8"), encoding='base64')
                item = InputGitTreeElement(
                    path=value.path,
                    mode=str(oct(value.mode))[2:],
                    type='blob',
                    sha=blob.sha
                )
                tree_elements.append(item)

        for file in files_to_remove:
            logging.debug(f"Delete file {file}")
            item = InputGitTreeElement(
                path=file,
                mode='100644',
                type='blob',
                sha=None
            )
            tree_elements.append(item)

        # repo_dir
        new_tree = self.__repo.create_git_tree(tree_elements, base_tree)
        commit = self.__repo.create_git_commit(
            message=commit_message,
            tree=new_tree,
            parents=[parent_commit]
        )

        self.__repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=commit.sha)

    def branch_exists(self, branch_name: str):
        remote_branch_name = f'origin/{branch_name}'

        return branch_name in self.__branches or remote_branch_name in self.__branches

    def open_pr(self,
                repo_dir,
                branch_name: str,
                original_component: AtmosComponent,
                updated_component: AtmosComponent) -> PullRequestCreationResponse:
        original_component_version_link = self.__build_component_version_link(original_component)
        updated_component_version_link = self.__build_component_version_link(updated_component)

        original_component_release_link = self.__build_component_release_tag_link(original_component)
        updated_component_release_link = self.__build_component_release_tag_link(updated_component)

        old_source_name, old_source_link = self.__build_get_source(original_component)
        new_source_name, new_source_link = self.__build_get_source(updated_component)

        title = self.__pr_title_template.render(component_name=original_component.name,
                                                source_name=old_source_name,
                                                old_version=original_component.version,
                                                new_version=updated_component.version)

        body = self.__pr_body_template.render(component_name=original_component.name,
                                              old_source_name=old_source_name,
                                              old_source_link=old_source_link,
                                              new_source_name=new_source_name,
                                              new_source_link=new_source_link,
                                              old_version=original_component.version,
                                              new_version=updated_component.version,
                                              old_version_link=original_component_version_link,
                                              new_version_link=updated_component_version_link,
                                              old_component_release_link=original_component_release_link,
                                              new_component_release_link=updated_component_release_link)

        response = PullRequestCreationResponse(branch_name, title, body, self.__config.pr_labels)

        if self.__config.dry_run:
            logging.info("Skipping pull request creation in dry-run mode")
            return response

        branch = self.__repo.get_branch(branch_name)
        repo = git.repo.Repo(repo_dir)
        pull_request: PullRequest = self.__repo.create_pull(title=title,
                                                            body=body,
                                                            base=repo.active_branch.name,
                                                            head=branch.name)

        pull_request.add_to_labels(*self.__config.pr_labels)

        response.pull_request = pull_request

        return response

    def get_open_prs_for_component(self, component_name: str):
        open_prs = []

        if not self.__pull_requests:
            self.__pull_requests = self.__repo.get_pulls(state='open')

        for pull_request in self.__pull_requests:
            pr_branch_name = pull_request.head.ref
            branch_prefixs = list(filter(None, [ BRANCH_PREFIX, component_name]))
            branch_prefix = '/'.join(branch_prefixs) + '/'
            # e.g. component-update/component-name/
            if pr_branch_name.startswith(branch_prefix): 
                open_prs.append(pull_request)

        return open_prs

    def close_pr(self, pull_request: PullRequest, message: str):
        pull_request.edit(state='closed')
        pull_request.create_issue_comment(message)
        self.__repo.get_git_ref(f'heads/{pull_request.head.ref}').delete()


    def __build_component_version_link(self, component: AtmosComponent):
        component_version_link = None

        version = component.version
        if "cloudposse-terraform-components" not in component.uri_repo:
            version = f"v{version.lstrip('v')}"

        if component.uri_repo.startswith('github.com'):
            normalized_repo_uri = self.__remove_git_suffix(component.uri_repo)
            component_version_link = f'https://{normalized_repo_uri}/tree/{version}/{component.uri_path}'
        elif component.uri_repo.startswith('https://github.com'):
            normalized_repo_uri = self.__remove_git_suffix(component.uri_repo)
            component_version_link = f'{normalized_repo_uri}/tree/{version}/{component.uri_path}'

        return component_version_link

    def __build_component_release_tag_link(self, component: AtmosComponent):
        component_release_tag_link = None
        version = component.version
        if "cloudposse-terraform-components" not in component.uri_repo:
            version = f"v{version.lstrip('v')}"

        if component.uri_repo.startswith('github.com'):
            normalized_repo_uri = self.__remove_git_suffix(component.uri_repo)
            component_release_tag_link = f'https://{normalized_repo_uri}/releases/tag/{version}'
        elif component.uri_repo.startswith('https://github.com'):
            normalized_repo_uri = self.__remove_git_suffix(component.uri_repo)
            component_release_tag_link = f'{normalized_repo_uri}/releases/tag/{version}'

        return component_release_tag_link

    def __build_get_source(self, component: AtmosComponent) -> Tuple[str, str]:
        match = re.match(r'(?:github\.com\/|@github\.com:)([\w\-_.]+)\/([\w\-_.]+)', component.uri_repo)

        if match:
            company = match.group(1)
            repo = self.__remove_git_suffix(match.group(2))
            source_name = f'{company}/{repo}'
            source_link = f'https://github.com/{source_name}'
        else:
            source_name = component.uri_repo
            source_link = component.uri_repo

        return source_name, source_link

    def __remove_git_suffix(self, repo_uri: str):
        if repo_uri.endswith('.git'):
            repo_uri = repo_uri[:-4]

        return repo_uri

    def __load_template(self, explicit_template: str, default_template_file: str):
        if explicit_template:
            template = Template(explicit_template)
        else:
            jenv = jinja2.Environment(loader=FileSystemLoader(TEMPLATES_DIR))
            template = jenv.get_template(default_template_file)

        return template
