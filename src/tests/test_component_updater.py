# pylint: disable=redefined-outer-name
# pylint: disable=wrong-import-position

from typing import List
import unittest.mock as mock
import os
import sys
import shutil
import pytest
import jinja2
from jinja2 import FileSystemLoader
from tests.fake_tools_manager import FakeToolsManager

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from component_updater import ComponentUpdater, ComponentUpdaterResponse, ComponentUpdaterResponseState  # noqa: E402
from github_provider import GitHubProvider                                                               # noqa: E402
from utils import io                                                                                     # noqa: E402
from config import Config                                                                                # noqa: E402


TEMPLATES_DIR = 'src/tests/templates'
FIXTURE_INFRA_REPO = 'src/tests/fixtures/infra-repo'
TERRAFORM_DIR = 'components/terraform'
DEFAULT_COMPONENT_TEMPLATE_FILE = 'component.yaml.j2'
ATMOS_COMPONENT_FILE = 'component.yaml'
TAG_1 = '1.107.0'
TAG_2 = '3.2.0'
TAG_3 = '10.2.1'


@pytest.fixture
def config():
    conf = Config('test/repo', io.create_tmp_dir(), TERRAFORM_DIR, False, 10, '*', '', '', True)
    conf.skip_component_repo_fetching = True
    return conf


def prepare_infra_repo(infra_dir: str):
    # copy fixture infra repo to temp test infra dir
    shutil.copytree(FIXTURE_INFRA_REPO, infra_dir, dirs_exist_ok=True)


def create_component(infra_dir: str,
                     name: str,
                     version: str,
                     uri=None):
    # create component folder with component name
    component_dir = os.path.join(infra_dir, TERRAFORM_DIR, name)
    io.create_dirs(component_dir)

    # render component.yaml
    uri = uri if uri else f'github.com/cloudposse/terraform-aws-components//modules/{name}?ref={{ .Version }}'
    template = jinja2.Environment(loader=FileSystemLoader(TEMPLATES_DIR)).get_template(DEFAULT_COMPONENT_TEMPLATE_FILE)
    component_content = template.render(name=name, uri=uri, version=version)
    io.save_string_to_file(os.path.join(component_dir, ATMOS_COMPONENT_FILE), component_content)


def prep_github_provider(config: Config):
    fake_github = mock.MagicMock()
    fake_github_provider = GitHubProvider(config, fake_github)
    fake_github_provider.branch_exists = mock.MagicMock(return_value=False)
    fake_github_provider.pr_for_branch_exists = mock.MagicMock(return_value=False)
    fake_github_provider.create_branch_and_push_all_changes = mock.MagicMock()
    return fake_github_provider


def test_no_version_specified(config: Config):
    # setup
    prepare_infra_repo(config.infra_repo_dir)
    create_component(config.infra_repo_dir, 'test_component_01', '')

    component_updater = ComponentUpdater(prep_github_provider(config), FakeToolsManager(TAG_3), config.infra_terraform_dirs, config)

    # test
    responses = component_updater.update()

    # validate
    assert len(responses) == 1
    assert responses[0].state == ComponentUpdaterResponseState.NO_VERSION_FOUND_IN_SOURCE_YAML


def test_not_valid_uri(config: Config):
    # setup
    prepare_infra_repo(config.infra_repo_dir)
    create_component(config.infra_repo_dir, 'test_component_01', TAG_1, 'github.com/cloudposse/terraform-aws-components.git')  # no path specified

    component_updater = ComponentUpdater(prep_github_provider(config), FakeToolsManager(TAG_3), config.infra_terraform_dirs, config)

    # test
    responses = component_updater.update()

    # validate
    assert len(responses) == 1
    assert responses[0].state == ComponentUpdaterResponseState.NOT_VALID_URI_FOUND_IN_SOURCE_YAML


def test_components_repo_is_not_a_git_repo(config: Config):
    # setup
    prepare_infra_repo(config.infra_repo_dir)
    create_component(config.infra_repo_dir, 'test_component_01', TAG_1)

    component_updater = ComponentUpdater(prep_github_provider(config), FakeToolsManager(TAG_3, is_valid_git_repo=False), config.infra_terraform_dirs, config)

    # test
    responses = component_updater.update()

    # validate
    assert len(responses) == 1
    assert responses[0].state == ComponentUpdaterResponseState.URI_IS_NOT_GIT_REPO


def test_components_repo_git_no_tags(config: Config):
    # setup
    prepare_infra_repo(config.infra_repo_dir)
    create_component(config.infra_repo_dir, 'test_component_01', TAG_1)

    component_updater = ComponentUpdater(prep_github_provider(config), FakeToolsManager(latest_tag=None), config.infra_terraform_dirs, config)

    # test
    responses = component_updater.update()

    # validate
    assert len(responses) == 1
    assert responses[0].state == ComponentUpdaterResponseState.NO_LATEST_TAG_FOUND_IN_COMPONENT_REPO


def test_components_repo_already_up_to_date(config: Config):
    # setup
    prepare_infra_repo(config.infra_repo_dir)
    create_component(config.infra_repo_dir, 'test_component_01', TAG_3)

    component_updater = ComponentUpdater(prep_github_provider(config), FakeToolsManager(TAG_3), config.infra_terraform_dirs, config)

    # test
    responses = component_updater.update()

    # validate
    assert len(responses) == 1
    assert responses[0].state == ComponentUpdaterResponseState.ALREADY_UP_TO_DATE


def test_components_remote_branch_exists(config: Config):
    # setup
    prepare_infra_repo(config.infra_repo_dir)
    create_component(config.infra_repo_dir, 'test_component_01', TAG_1)

    fake_github_provider = prep_github_provider(config)
    fake_github_provider.branch_exists = mock.MagicMock(return_value=True)
    component_updater = ComponentUpdater(fake_github_provider, FakeToolsManager(TAG_3), config.infra_terraform_dirs, config)

    # test
    responses = component_updater.update()

    # validate
    assert len(responses) == 1
    assert responses[0].state == ComponentUpdaterResponseState.REMOTE_BRANCH_FOR_COMPONENT_UPDATER_ALREADY_EXIST


def test_components_pr_exists(config: Config):
    # setup
    prepare_infra_repo(config.infra_repo_dir)
    create_component(config.infra_repo_dir, 'test_component_01', TAG_1)

    fake_github_provider = prep_github_provider(config)
    fake_github_provider.pr_for_branch_exists = mock.MagicMock(return_value=True)
    component_updater = ComponentUpdater(fake_github_provider, FakeToolsManager(TAG_3), config.infra_terraform_dirs, config)

    # test
    responses = component_updater.update()

    # validate
    assert len(responses) == 1
    assert responses[0].state == ComponentUpdaterResponseState.PR_FOR_BRANCH_ALREADY_EXISTS


def test_not_vendored_component_with_not_skip_vendoring(config: Config):
    # setup
    prepare_infra_repo(config.infra_repo_dir)
    create_component(config.infra_repo_dir, 'test_component_01', TAG_1)

    component_updater = ComponentUpdater(prep_github_provider(config), FakeToolsManager(TAG_3), config.infra_terraform_dirs, config)

    # test
    responses = component_updater.update()

    # validate
    assert len(responses) == 1

    response = responses[0]

    assert response.state == ComponentUpdaterResponseState.UPDATED

    # checking that component was vendored
    assert os.path.exists(os.path.join(response.component.infra_repo_dir, TERRAFORM_DIR, response.component.name, 'main.tf'))
    assert os.path.exists(os.path.join(response.component.infra_repo_dir, TERRAFORM_DIR, response.component.name, 'output.tf'))


def test_not_vendored_component_with_skip_vendoring(config: Config):
    # setup
    config.skip_component_vendoring = True

    prepare_infra_repo(config.infra_repo_dir)
    create_component(config.infra_repo_dir, 'test_component_01', TAG_1)

    component_updater = ComponentUpdater(prep_github_provider(config), FakeToolsManager(TAG_3), config.infra_terraform_dirs, config)

    # test
    responses = component_updater.update()

    # validate
    assert len(responses) == 1

    response = responses[0]

    assert response.state == ComponentUpdaterResponseState.COMPONENT_NOT_VENDORED

    # checking that component was vendored
    assert not os.path.exists(os.path.join(response.component.infra_repo_dir, TERRAFORM_DIR, response.component.name, 'main.tf'))
    assert not os.path.exists(os.path.join(response.component.infra_repo_dir, TERRAFORM_DIR, response.component.name, 'output.tf'))


def test_with_changes_found(config: Config):
    # setup
    prepare_infra_repo(config.infra_repo_dir)
    create_component(config.infra_repo_dir, 'test_component_01', TAG_1)

    component_updater = ComponentUpdater(prep_github_provider(config), FakeToolsManager(TAG_3), config.infra_terraform_dirs, config)

    # test
    responses = component_updater.update()

    # validate
    assert len(responses) == 1

    response = responses[0]

    assert response.state == ComponentUpdaterResponseState.UPDATED
    assert os.path.exists(os.path.join(response.component.infra_repo_dir, TERRAFORM_DIR, response.component.name, 'main.tf'))


def test_no_changes_found(config: Config):
    # setup
    prepare_infra_repo(config.infra_repo_dir)
    create_component(config.infra_repo_dir, 'test_component_01', TAG_1)
    shutil.copyfile(os.path.join(os.getcwd(), 'src/tests/fixtures/terraform-aws-components/', TAG_1, 'modules/test_component_01/main.tf'),
                    os.path.join(config.infra_repo_dir, TERRAFORM_DIR, 'test_component_01', 'main.tf'))

    component_updater = ComponentUpdater(prep_github_provider(config), FakeToolsManager(TAG_2), config.infra_terraform_dirs, config)

    # test
    responses = component_updater.update()

    # validate
    assert len(responses) == 1

    response = responses[0]

    assert response.state == ComponentUpdaterResponseState.NO_CHANGES_FOUND
    assert os.path.exists(os.path.join(response.component.infra_repo_dir, TERRAFORM_DIR, response.component.name, 'main.tf'))


def test_multiple_components_updated(config: Config):
    # setup
    prepare_infra_repo(config.infra_repo_dir)
    create_component(config.infra_repo_dir, 'test_component_01', TAG_1)
    create_component(config.infra_repo_dir, 'test_component_02', TAG_1)

    component_updater = ComponentUpdater(prep_github_provider(config), FakeToolsManager(TAG_3), config.infra_terraform_dirs, config)

    # test
    responses = component_updater.update()

    # validate
    assert len(responses) == 2
    assert responses[0].state == ComponentUpdaterResponseState.UPDATED
    assert responses[1].state == ComponentUpdaterResponseState.UPDATED


def test_some_components_updated(config: Config):
    # setup
    prepare_infra_repo(config.infra_repo_dir)
    create_component(config.infra_repo_dir, 'test_component_01', TAG_1)
    create_component(config.infra_repo_dir, 'test_component_02', TAG_1)

    component_updater = ComponentUpdater(prep_github_provider(config), FakeToolsManager(TAG_2), config.infra_terraform_dirs, config)

    # test
    responses = component_updater.update()

    # validate
    assert len(responses) == 2
    assert responses[0].state == ComponentUpdaterResponseState.NO_CHANGES_FOUND
    assert responses[1].state == ComponentUpdaterResponseState.UPDATED


def test_some_vendored_and_some_not(config: Config):
    # setup
    config.skip_component_vendoring = True
    prepare_infra_repo(config.infra_repo_dir)
    create_component(config.infra_repo_dir, 'test_component_01', TAG_1)
    create_component(config.infra_repo_dir, 'test_component_02', TAG_1)
    shutil.copyfile(os.path.join(os.getcwd(), 'src/tests/fixtures/terraform-aws-components/', TAG_1, 'modules/test_component_01/main.tf'),
                    os.path.join(config.infra_repo_dir, TERRAFORM_DIR, 'test_component_01', 'main.tf'))

    component_updater = ComponentUpdater(prep_github_provider(config), FakeToolsManager(TAG_2), config.infra_terraform_dirs, config)

    # test
    responses = component_updater.update()

    # validate
    assert len(responses) == 2
    assert responses[0].state == ComponentUpdaterResponseState.NO_CHANGES_FOUND
    assert responses[1].state == ComponentUpdaterResponseState.COMPONENT_NOT_VENDORED


def test_missing_component(config: Config):
    # setup
    prepare_infra_repo(config.infra_repo_dir)
    create_component(config.infra_repo_dir, 'missing_component', TAG_1)

    component_updater = ComponentUpdater(prep_github_provider(config), FakeToolsManager(TAG_3), config.infra_terraform_dirs, config)

    # test
    responses = component_updater.update()

    # validate
    assert len(responses) == 1
    assert responses[0].state == ComponentUpdaterResponseState.FAILED_TO_VENDOR_COMPONENT


@pytest.mark.parametrize("include, exclude, expected_updated_components", [
    ([''], [''], []),
    (['*'], [''], ['test_component_01', 'test_component_02', 'test_component_03']),
    (['test_component_*'], [''], ['test_component_01', 'test_component_02', 'test_component_03']),
    (['*component_*'], [''], ['test_component_01', 'test_component_02', 'test_component_03']),
    (['component_'], [''], []),
    (['test_component_*'], ['*04*'], ['test_component_01', 'test_component_02', 'test_component_03']),
    (['test_component_*'], ['*02*'], ['test_component_01', 'test_component_03']),
    ([''], ['test*'], []),
])
def test_include_and_exclude(config: Config, include: List[str], exclude: List[str], expected_updated_components: List[str]):
    # setup
    config.include = include
    config.exclude = exclude
    prepare_infra_repo(config.infra_repo_dir)
    create_component(config.infra_repo_dir, 'test_component_01', TAG_1)
    create_component(config.infra_repo_dir, 'test_component_02', TAG_1)
    create_component(config.infra_repo_dir, 'test_component_03', TAG_1)

    component_updater = ComponentUpdater(prep_github_provider(config), FakeToolsManager(TAG_3), config.infra_terraform_dirs, config)

    # test
    responses = component_updater.update()

    # validate
    assert len(responses) == len(expected_updated_components)
    names = [response.component.name for response in responses]
    assert sorted(names) == sorted(expected_updated_components)


def test_default_title_body_and_labels(config: Config):
    # setup
    prepare_infra_repo(config.infra_repo_dir)
    create_component(config.infra_repo_dir, 'test_component_01', TAG_1)

    component_updater = ComponentUpdater(prep_github_provider(config), FakeToolsManager(TAG_3), config.infra_terraform_dirs, config)

    # test
    responses: List[ComponentUpdaterResponse] = component_updater.update()

    # validate
    assert len(responses) == 1

    response = responses[0]

    assert response.state == ComponentUpdaterResponseState.UPDATED
    assert response.pull_request_creation_response is not None
    assert response.pull_request_creation_response.title == "Component `test_component_01` update from 1.107.0 → 10.2.1"
    assert 'This is an auto-generated PR that updates component `test_component_01` to version `10.2.1`.' in response.pull_request_creation_response.body
    assert '| **Component**      | `test_component_01`                 |' in response.pull_request_creation_response.body
    assert response.pull_request_creation_response.labels == ['component-update']


def test_updated_title_body_and_labels(config: Config):
    # setup
    config.pr_title_template = "Updated `{{ component_name }}` to version {{ new_version }}"
    config.pr_body_template = "Updated `{{ component_name }}` to version {{ new_version }}"
    config.pr_labels = ['component-update', 'auto-update', 'infra']

    prepare_infra_repo(config.infra_repo_dir)
    create_component(config.infra_repo_dir, 'test_component_01', TAG_1)

    component_updater = ComponentUpdater(prep_github_provider(config), FakeToolsManager(TAG_3), config.infra_terraform_dirs, config)

    # test
    responses: List[ComponentUpdaterResponse] = component_updater.update()

    # validate
    assert len(responses) == 1

    response = responses[0]

    assert response.state == ComponentUpdaterResponseState.UPDATED
    assert response.pull_request_creation_response is not None
    assert response.pull_request_creation_response.title == "Updated `test_component_01` to version 10.2.1"
    assert response.pull_request_creation_response.body == 'Updated `test_component_01` to version 10.2.1'
    assert response.pull_request_creation_response.labels == ['component-update', 'auto-update', 'infra']
