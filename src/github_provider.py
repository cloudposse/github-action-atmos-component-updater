import jinja2
import git.repo
from github import Github
from github.PullRequest import PullRequest
from jinja2 import FileSystemLoader
from atmos_component import AtmosComponent

BRANCH_PREFIX = 'component-update'
TEMPLATES_DIR = 'src/templates'
GITHUB_PULL_REQUEST_LABEL = 'component-update'
PR_TITLE_TEMPLATE = "Component `{component_name}` update from {old_version} → {new_version}"


class GitHubProvider:
    def __init__(self, api_token: str, repo_name: str):
        self.__github = Github(api_token)
        self.__repo = self.__github.get_repo(repo_name)
        self.__pull_requests = None
        jenv = jinja2.Environment(loader=FileSystemLoader(TEMPLATES_DIR))
        self.__pr_body_template = jenv.get_template('pr_body.md')

    def build_component_branch_name(self, component_name: str, tag: str):
        return f'{BRANCH_PREFIX}/{component_name}/{tag}'

    def get_branches(self, repo_dir: str):
        branches = []

        repo = git.repo.Repo(repo_dir)

        for branch in repo.heads:
            branches.append(branch.name)

        remote_branches = repo.remote().refs

        for branch in remote_branches:
            branches.append(branch.name)

        return set(branches)

    def create_branch_and_push_all_changes(self, repo_dir: str, branch_name: str, commit_message: str):
        repo = git.repo.Repo(repo_dir)

        new_branch = repo.create_head(branch_name)

        repo.git.checkout(new_branch)
        repo.git.add("-A")
        repo.index.commit(commit_message)
        repo.git.push("--set-upstream", "origin", branch_name)

    def branch_exists(self, repo_dir: str, branch_name: str):
        branches = self.get_branches(repo_dir)
        remote_branch_name = f'origin/{branch_name}'

        return branch_name in branches or remote_branch_name in branches

    def open_pr(self, branch_name: str, original_component: AtmosComponent, updated_component: AtmosComponent):
        branch = self.__repo.get_branch(branch_name)

        title = PR_TITLE_TEMPLATE.format(component_name=original_component.name,
                                         old_version=original_component.version,
                                         new_version=updated_component.version)

        original_component_version_link = self.__build_component_version_link(original_component)
        updated_component_version_link = self.__build_component_version_link(updated_component)

        original_component_release_link = self.__build_component_release_tag_link(original_component)
        updated_component_release_link = self.__build_component_release_tag_link(updated_component)

        body = self.__pr_body_template.render(component_name=original_component.name,
                                              old_version=original_component.version,
                                              new_version=updated_component.version,
                                              old_version_link=original_component_version_link,
                                              new_version_link=updated_component_version_link,
                                              old_component_release_link=original_component_release_link,
                                              new_component_release_link=updated_component_release_link)

        pull_request: PullRequest = self.__repo.create_pull(title=title,
                                                            body=body,
                                                            base=self.__repo.default_branch,
                                                            head=branch.name)

        pull_request.add_to_labels(GITHUB_PULL_REQUEST_LABEL)

        return pull_request

    def get_open_prs_for_component(self, component_name: str):
        open_prs = []

        if not self.__pull_requests:
            self.__pull_requests = self.__repo.get_pulls(state='open')

        for pull_request in self.__pull_requests:
            pr_branch_name = pull_request.head.ref

            if pr_branch_name.startswith(f'{BRANCH_PREFIX}/{component_name}/'):
                open_prs.append(pull_request)

        return open_prs

    def close_pr(self, pull_request: PullRequest, message: str):
        pull_request.edit(state='closed')
        pull_request.create_issue_comment(message)

    def __build_component_version_link(self, component: AtmosComponent):
        component_version_link = None

        if component.uri_repo.startswith('github.com'):
            normalized_repo_uri = self.__remove_git_suffix(component.uri_repo)
            component_version_link = f'https://{normalized_repo_uri}/tree/{component.version}/{component.uri_path}'
        elif component.uri_repo.startswith('https://github.com'):
            normalized_repo_uri = self.__remove_git_suffix(component.uri_repo)
            component_version_link = f'{normalized_repo_uri}/tree/{component.version}/{component.uri_path}'

        return component_version_link

    def __build_component_release_tag_link(self, component: AtmosComponent):
        component_release_tag_link = None

        if component.uri_repo.startswith('github.com'):
            normalized_repo_uri = self.__remove_git_suffix(component.uri_repo)
            component_release_tag_link = f'https://{normalized_repo_uri}/releases/tag/{component.version}'
        elif component.uri_repo.startswith('https://github.com'):
            normalized_repo_uri = self.__remove_git_suffix(component.uri_repo)
            component_release_tag_link = f'{normalized_repo_uri}/releases/tag/{component.version}'

        return component_release_tag_link

    def __remove_git_suffix(self, repo_uri: str):
        if repo_uri.endswith('.git'):
            repo_uri = repo_uri[:-4]

        return repo_uri
