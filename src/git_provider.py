import git

BRANCH_PREFIX = 'component-update'


class GitProvider:
    def __init__(self, repo_dir: str):
        self.__repo_dir = repo_dir
        self.__repo = git.Repo(repo_dir)

    def get_component_branch_name(self, component_name: str, version: str):
        return f'component-update/{component_name}/{version}'

    def get_default_branch(self):
        return self.__repo.heads[self.__repo.active_branch.name].remote_head

    def get_branches(self):
        branches = []

        for branch in self.__repo.heads:
            branches.append(branch.name)

        remote_branches = self.__repo.remote().refs

        for branch in remote_branches:
            branches.append(branch.name)

        return set(branches)

    def create_branch_and_push_all_changes(self, branch_name: str, commit_message: str):
        new_branch = self.__repo.create_head(branch_name)
        self.__repo.git.checkout(new_branch)
        self.__repo.git.add("-A")
        self.__repo.index.commit(commit_message)
        self.__repo.git.push("--set-upstream", "origin", branch_name)

    def branch_exists(self, branch_name: str):
        branches = self.get_branches()
        return branch_name in branches
