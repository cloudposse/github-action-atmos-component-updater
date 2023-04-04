import unittest.mock as mock
import os
import sys
import shutil
import jinja2
from jinja2 import FileSystemLoader

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# pylint: disable=wrong-import-position
from component_updater import ComponentUpdater, ComponentUpdaterResponseState  # noqa: E402
from github_provider import GitHubProvider                                     # noqa: E402
from utils import io                                                           # noqa: E402

TEMPLATES_DIR = 'src/tests/templates'
TERRAFORM_DIR = 'components/terraform'
COMPONENT_TEMPLATE = jinja2.Environment(loader=FileSystemLoader(TEMPLATES_DIR)).get_template('component.yaml.j2')


def create_component(name: str, uri: str, version: str, infra_dir: str, stub_infra_dir='infra-repo-01-not-vendored'):
    shutil.copytree('src/tests/test_data/' + stub_infra_dir, infra_dir, dirs_exist_ok=True)

    component_content = COMPONENT_TEMPLATE.render(name=name, uri=uri, version=version)
    component_dir = os.path.join(infra_dir, TERRAFORM_DIR, name)
    io.create_dirs(component_dir)
    io.save_string_to_file(os.path.join(component_dir, 'component.yaml'), component_content)


def test_no_version_specified():
    # setup
    infra_dir = io.create_tmp_dir()
    components_download_dir = io.create_tmp_dir()
    create_component('test_component', 'github.com/cloudposse/terraform-aws-components.git//modules/account-settings?ref={{ .Version }}', '', infra_dir)
    fake_github = mock.MagicMock()
    fake_github_provider = GitHubProvider('test/repo', fake_github)
    component_updater = ComponentUpdater(fake_github_provider, infra_dir, TERRAFORM_DIR, '*', '', '',
                                         components_download_dir=components_download_dir, skip_component_repo_fetching=True)

    # test
    responses = component_updater.update()

    # validate
    assert len(responses) == 1
    assert responses[0].state == ComponentUpdaterResponseState.NO_VERSION_FOUND_IN_SOURCE_YAML


def test_not_valid_uri():
    # setup
    infra_dir = io.create_tmp_dir()
    components_download_dir = io.create_tmp_dir()
    create_component('test_component', 'github.com/cloudposse/terraform-aws-components.git', '1.107.0', infra_dir)
    fake_github = mock.MagicMock()
    fake_github_provider = GitHubProvider('test/repo', fake_github)
    component_updater = ComponentUpdater(fake_github_provider, infra_dir, TERRAFORM_DIR, '*', '', '',
                                         components_download_dir=components_download_dir, skip_component_repo_fetching=True)

    # test
    responses = component_updater.update()

    # validate
    assert len(responses) == 1
    assert responses[0].state == ComponentUpdaterResponseState.NOT_VALID_URI_FOUND_IN_SOURCE_YAML


def test_components_repo_is_not_a_git_repo():
    # setup
    infra_dir = io.create_tmp_dir()
    components_download_dir = io.create_tmp_dir()
    create_component('test_component', 's3://components-bucket/modules/account-settings?ref={{ .Version }}', '1.107.0', infra_dir)
    fake_github = mock.MagicMock()
    fake_github_provider = GitHubProvider('test/repo', fake_github)
    component_updater = ComponentUpdater(fake_github_provider, infra_dir, TERRAFORM_DIR, '*', '', '',
                                         components_download_dir=components_download_dir, skip_component_repo_fetching=True)

    # test
    responses = component_updater.update()

    # validate
    assert len(responses) == 1
    assert responses[0].state == ComponentUpdaterResponseState.URI_IS_NOT_GIT_REPO


def test_components_repo_git_no_tags():
    # setup
    infra_dir = io.create_tmp_dir()
    components_download_dir = 'src/tests/test_data/invalid-no-tags-terraform-aws-components'
    create_component('test_component', 'github.com/cloudposse/terraform-aws-components//modules/account-settings?ref={{ .Version }}', '1.107.0', infra_dir)
    fake_github = mock.MagicMock()
    fake_github_provider = GitHubProvider('test/repo', fake_github)
    component_updater = ComponentUpdater(fake_github_provider, infra_dir, TERRAFORM_DIR, '*', '', '',
                                         components_download_dir=components_download_dir, skip_component_repo_fetching=True)

    # test
    responses = component_updater.update()

    # validate
    assert len(responses) == 1
    assert responses[0].state == ComponentUpdaterResponseState.NO_LATEST_TAG_FOUND_IN_COMPONENT_REPO


def test_components_repo_already_up_to_date():
    # setup
    infra_dir = io.create_tmp_dir()
    components_download_dir = 'src/tests/test_data/terraform-aws-components'
    create_component('test_component', 'github.com/cloudposse/terraform-aws-components//modules/account-settings?ref={{ .Version }}', '10.2.1', infra_dir)
    fake_github = mock.MagicMock()
    fake_github_provider = GitHubProvider('test/repo', fake_github)
    component_updater = ComponentUpdater(fake_github_provider, infra_dir, TERRAFORM_DIR, '*', '', '',
                                         components_download_dir=components_download_dir, skip_component_repo_fetching=True)

    # test
    responses = component_updater.update()

    # validate
    assert len(responses) == 1
    assert responses[0].state == ComponentUpdaterResponseState.ALREADY_UP_TO_DATE


def test_components_remote_branch_exists():
    # setup
    infra_dir = io.create_tmp_dir()
    components_download_dir = 'src/tests/test_data/terraform-aws-components'
    create_component('test_component', 'github.com/cloudposse/terraform-aws-components//modules/account-settings?ref={{ .Version }}', '1.107.0', infra_dir)
    fake_github = mock.MagicMock()
    fake_github_provider = GitHubProvider('test/repo', fake_github)
    fake_github_provider.branch_exists = mock.MagicMock(return_value=True)
    component_updater = ComponentUpdater(fake_github_provider, infra_dir, TERRAFORM_DIR, '*', '', '',
                                         components_download_dir=components_download_dir, skip_component_repo_fetching=True)

    # test
    responses = component_updater.update()

    # validate
    assert len(responses) == 1
    assert responses[0].state == ComponentUpdaterResponseState.REMOTE_BRANCH_FOR_COMPONENT_UPDATER_ALREADY_EXIST


def test_not_vendored_component_with_not_skip_vendoring():
    # setup
    infra_dir = io.create_tmp_dir()
    components_download_dir = 'src/tests/test_data/terraform-aws-components'
    create_component('test_component', os.getcwd() + '/src/tests/test_data/terraform-aws-components//modules/test-component?ref={{ .Version }}', '1.107.0', infra_dir)
    fake_github = mock.MagicMock()
    fake_github_provider = GitHubProvider('test/repo', fake_github)
    fake_github_provider.branch_exists = mock.MagicMock(return_value=False)
    fake_github_provider.create_branch_and_push_all_changes = mock.MagicMock()
    component_updater = ComponentUpdater(fake_github_provider, infra_dir, TERRAFORM_DIR, '*', '', '',
                                         components_download_dir=components_download_dir, skip_component_repo_fetching=True)

    # test
    responses = component_updater.update()

    # validate
    assert len(responses) == 1

    response = responses[0]

    assert response.state == ComponentUpdaterResponseState.UPDATED

    # checking that component was vendored
    assert os.path.exists(os.path.join(response.component.infra_repo_dir, TERRAFORM_DIR, response.component.name, 'main.tf'))


def test_not_vendored_component_with_skip_vendoring():
    # setup
    infra_dir = io.create_tmp_dir()
    components_download_dir = 'src/tests/test_data/terraform-aws-components'
    create_component('test_component', os.getcwd() + '/src/tests/test_data/terraform-aws-components//modules/test-component?ref={{ .Version }}', '1.107.0', infra_dir)
    fake_github = mock.MagicMock()
    fake_github_provider = GitHubProvider('test/repo', fake_github)
    fake_github_provider.branch_exists = mock.MagicMock(return_value=False)
    fake_github_provider.create_branch_and_push_all_changes = mock.MagicMock()
    component_updater = ComponentUpdater(fake_github_provider, infra_dir, TERRAFORM_DIR, '*', '', '',
                                         components_download_dir=components_download_dir, skip_component_repo_fetching=True, skip_component_vendoring=True)

    # test
    responses = component_updater.update()

    # validate
    assert len(responses) == 1

    response = responses[0]

    assert response.state == ComponentUpdaterResponseState.UPDATED

    # checking that component was vendored
    assert not os.path.exists(os.path.join(response.component.infra_repo_dir, TERRAFORM_DIR, response.component.name, 'main.tf'))


def test_with_changes_found():
    # setup
    infra_dir = io.create_tmp_dir()
    components_download_dir = 'src/tests/test_data/terraform-aws-components'
    create_component('test_component', os.getcwd() + '/src/tests/test_data/terraform-aws-components//modules/test-component?ref={{ .Version }}', '1.107.0', infra_dir, 'infra-repo-02-vendored')
    fake_github = mock.MagicMock()
    fake_github_provider = GitHubProvider('test/repo', fake_github)
    fake_github_provider.branch_exists = mock.MagicMock(return_value=False)
    fake_github_provider.create_branch_and_push_all_changes = mock.MagicMock()
    component_updater = ComponentUpdater(fake_github_provider, infra_dir, TERRAFORM_DIR, '*', '', '',
                                         components_download_dir=components_download_dir, skip_component_repo_fetching=True)

    # test
    responses = component_updater.update()

    # validate
    assert len(responses) == 1

    response = responses[0]

    assert response.state == ComponentUpdaterResponseState.UPDATED
    assert os.path.exists(os.path.join(response.component.infra_repo_dir, TERRAFORM_DIR, response.component.name, 'main.tf'))


def test_no_changes_found():
    # setup
    infra_dir = io.create_tmp_dir()
    components_download_dir = 'src/tests/test_data/terraform-aws-components'
    create_component('test_component', os.getcwd() + '/src/tests/test_data/terraform-aws-components//modules/test-component?ref={{ .Version }}', '1.107.0', infra_dir, 'infra-repo-03-vendored-no-changes')
    fake_github = mock.MagicMock()
    fake_github_provider = GitHubProvider('test/repo', fake_github)
    fake_github_provider.branch_exists = mock.MagicMock(return_value=False)
    fake_github_provider.create_branch_and_push_all_changes = mock.MagicMock()
    component_updater = ComponentUpdater(fake_github_provider, infra_dir, TERRAFORM_DIR, '*', '', '',
                                         components_download_dir=components_download_dir, skip_component_repo_fetching=True)

    # test
    responses = component_updater.update()

    # validate
    assert len(responses) == 1

    response = responses[0]

    assert response.state == ComponentUpdaterResponseState.NO_CHANGES_FOUND
    assert os.path.exists(os.path.join(response.component.infra_repo_dir, TERRAFORM_DIR, response.component.name, 'main.tf'))
