import git

BRANCH_PREFIX = 'component-update'


class GitProvider:
    def build_component_branch_name(self, component_name: str, tag: str):
        return f'{BRANCH_PREFIX}/{component_name}/{tag}'

    def get_branches(self, repo_dir: str):
        branches = []

        repo = git.Repo(repo_dir)

        for branch in repo.heads:
            branches.append(branch.name)

        remote_branches = repo.remote().refs

        for branch in remote_branches:
            branches.append(branch.name)

        return set(branches)

    def create_branch_and_push_all_changes(self, repo_dir: str, branch_name: str, commit_message: str):
        repo = git.Repo(repo_dir)

        new_branch = repo.create_head(branch_name)

        repo.git.checkout(new_branch)
        repo.git.add("-A")
        repo.index.commit(commit_message)
        repo.git.push("--set-upstream", "origin", branch_name)

    def branch_exists(self, repo_dir: str, branch_name: str):
        branches = self.get_branches(repo_dir)
        remote_branch_name = f'origin/{branch_name}'

        return branch_name in branches or remote_branch_name in branches
