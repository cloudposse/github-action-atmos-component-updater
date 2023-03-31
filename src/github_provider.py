from github import Github, PullRequest
from atmos_component import AtmosComponent

BRANCH_PREFIX = 'component-update'
GITHUB_PULL_REQUEST_LABEL = 'component-update'
PR_TITLE_TEMPLATE = "Component `{component_name}` update from {old_version} to {new_version}"
PR_BODY_TEMPLATE = """
## what

This is an auto-generated PR that updates component `{component_name}` to version `{new_version}`.

| Meta               | Details             |
|:-------------------|:--------------------|
| **Component name** | `{component_name}`  |
| **Old Version**    | {old_version_link}  |
| **New Version**    | {new_version_link}  |

## why

[Cloud Posse](https://cloudposse.com) recommends upgrading Terraform components regularly to maintain a secure, efficient, and well-supported infrastructure. In doing so, you'll benefit from the latest features, improved compatibility, easier upgrades, and ongoing support while mitigating potential risks and meeting compliance requirements.

- **Enhanced Security**: Updating to the latest version ensures you have the most up-to-date security patches and vulnerability fixes, safeguarding your infrastructure against potential threats.
- **Improved Performance**: Newer versions of Terraform components often come with performance optimizations, enabling your infrastructure to run more efficiently and use resources more effectively.
- **Access to New Features**: Regularly updating ensures access to the latest features and improvements, allowing you to take advantage of new functionality that can help streamline your infrastructure management process.
- **Better Compatibility:** Staying current with Terraform component updates ensures that you maintain compatibility with other components that may also be updating. This can prevent integration issues and ensure smooth operation within your technology stack.
- **Easier Upgrades:** By updating components regularly, you can avoid the challenges of upgrading multiple versions at once, which can be time-consuming and potentially introduce breaking changes. Incremental updates make it easier to identify and resolve issues as they arise.
- **Ongoing Support:** Updated components are more likely to receive continued support from the developer community, including bug fixes, security patches, and new feature development. Falling too far behind can leave your infrastructure unsupported and more vulnerable to issues.
- **Compliance Requirements:** In some cases, regularly updating your Terraform components may be necessary to meet regulatory or industry compliance requirements, ensuring that your infrastructure adheres to specific standards.

## FAQ

### What to do if there are breaking changes?
Please let Cloud Posse know by raising an issue.

### What to do if there are no changes to the deployed infrastructure?
We recommend merging the PR, that way it's easier to identify when there are breaking changes in the future and at what version.

### What to do if there are changes due to the updates?
We recommend carefully reviewing the plan to ensure there's nothing destructive before applying any changes in the automated PRs. If the changes seem reasonable, confirm and deploy. If the changes are unexpected, consider raising an issue.
"""


class GitHubProvider:
    def __init__(self, api_token: str, repo_name: str):
        self.__github = Github(api_token)
        self.__repo = self.__github.get_repo(repo_name)
        self.__pull_requests = []

    def open_pr(self, branch_name: str, original_component: AtmosComponent, updated_component: AtmosComponent):
        branch = self.__repo.get_branch(branch_name)

        original_component_version = self.__build_component_version(original_component)
        updated_component_version = self.__build_component_version(updated_component)

        title = PR_TITLE_TEMPLATE.format(component_name=original_component.get_name(),
                                         old_version=original_component.get_version(),
                                         new_version=updated_component.get_version())

        body = PR_BODY_TEMPLATE.format(component_name=original_component.get_name(),
                                       old_version=original_component.get_version(),
                                       new_version=updated_component.get_version(),
                                       old_version_link=original_component_version,
                                       new_version_link=updated_component_version)

        pr: PullRequest = self.__repo.create_pull(title=title,
                                                  body=body,
                                                  base=self.__repo.default_branch,
                                                  head=branch.name)

        pr.add_to_labels(GITHUB_PULL_REQUEST_LABEL)

        return pr

    def get_open_prs_for_component(self, component_name: str):
        open_prs = []

        if len(self.__pull_requests) == 0:
            self.__pull_requests = self.__repo.get_pulls(state='open')

        for pr in self.__pull_requests:
            pr_branch_name = pr.head.ref

            if pr_branch_name.startswith(f'{BRANCH_PREFIX}/{component_name}/'):
                open_prs.append(pr)

        return open_prs

    def close_pr(self, pr: PullRequest, message: str):
        pr.edit(state='closed')
        pr.create_comment(message)

    def __build_component_version(self, component):
        component_version = f'`{component.get_version()}`'

        if component.get_uri_repo().startswith('github.com'):
            normalized_repo_uri = self.__remove_git_suffix(component.get_uri_repo())
            component_version = f'[`{component.get_version()}`](https://{normalized_repo_uri}/tree/{component.get_version()}/{component.get_component_uri_path()})'
        elif component.get_uri_repo().startswith('https://github.com'):
            normalized_repo_uri = self.__remove_git_suffix(component.get_uri_repo())
            component_version = f'[`{component.get_version()}`]({normalized_repo_uri}/tree/{component.get_version()}/{component.get_component_uri_path()})'

        return component_version

    def __remove_git_suffix(self, repo_uri):
        repo_uri = repo_uri

        if repo_uri.endswith('.git'):
            repo_uri = repo_uri[:-4]

        return repo_uri
