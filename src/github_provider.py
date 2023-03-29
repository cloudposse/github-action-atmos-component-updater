from github import Github, PullRequest

BRANCH_PREFIX = 'component-update'
PR_TITLE_TEMPLATE = "Component {component_name} update from {old_version} to {new_version}"
PR_BODY_TEMPLATE = """
## what

This is an auto-generated PR that updates component `{component_name}` to version `{new_version}`.

| Meta               | Details            |
|:-------------------|:-------------------|
| **Component name** | `{component_name}` |
| **Old Version**    | `{old_version}`    |
| **New Version**    | `{new_version}`    |

## why

Use component `{component_name}` the latest available version `{new_version}` 
"""


class GitHubProvider:
    def __init__(self, api_token: str, repo_name: str):
        self.__github = Github(api_token)
        self.__repo = self.__github.get_repo(repo_name)

    def open_pr(self, branch_name: str, component_name: str, old_version: str, new_version: str):
        branch = self.__repo.get_branch(branch_name)

        title = PR_TITLE_TEMPLATE.format(component_name=component_name,
                                         old_version=old_version,
                                         new_version=new_version)

        body = PR_BODY_TEMPLATE.format(component_name=component_name,
                                       old_version=old_version,
                                       new_version=new_version)

        pr: PullRequest = self.__repo.create_pull(title=title,
                                                  body=body,
                                                  base=self.__repo.default_branch,
                                                  head=branch.name)
        return pr

    def get_open_prs_for_component(self, component_name: str):
        open_prs = []
        pull_requests = self.__repo.get_pulls(state='open')

        for pr in pull_requests:
            pr_branch_name = pr.head.ref

            if pr_branch_name.startswith(f'{BRANCH_PREFIX}/{component_name}/'):
                open_prs.append(pr)

        return open_prs

    def close_pr(self, pr: PullRequest, message: str):
        pr.edit(state='closed', body=message)
