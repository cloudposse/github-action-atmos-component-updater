# pylint: disable=redefined-outer-name
# pylint: disable=wrong-import-position

from typing import List, Optional
import unittest.mock as mock
import os
import sys
import shutil
import pytest
import jinja2
from jinja2 import FileSystemLoader

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from component_updater import ComponentUpdater, ComponentUpdaterResponseState  # noqa: E402
from github_provider import GitHubProvider                                     # noqa: E402
from utils import io                                                           # noqa: E402
from config import Config                                                      # noqa: E402


TEMPLATES_DIR = 'src/tests/templates'
FIXTURE_INFRA_REPO = 'src/tests/fixtures/infra-repo'
TERRAFORM_DIR = 'components/terraform'
TERRAFORM_COMPONENTS_REPO_PATH = 'src/tests/fixtures/terraform-aws-components'
TERRAFORM_COMPONENTS_INVALID_REPO_PATH = 'src/tests/fixtures/terraform-aws-components-02-invalid-no-tags'
DEFAULT_COMPONENT_TEMPLATE_FILE = 'component.yaml.j2'
ATMOS_COMPONENT_FILE = 'component.yaml'
EXISTING_TAG = '10.2.1'


@pytest.fixture
def config():
    conf = Config('test/repo', io.create_tmp_dir(), TERRAFORM_DIR, False, 10, '*', '', '', True, '')
    conf.components_download_dir = TERRAFORM_COMPONENTS_REPO_PATH
    conf.skip_component_repo_fetching = True
    return conf


def prepare_infra_repo(infra_dir: str):
    # copy fixture infra repo to temp test infra dir
    shutil.copytree(FIXTURE_INFRA_REPO, infra_dir, dirs_exist_ok=True)


def create_component(infra_dir: str,
                     name: str,
                     version: str,
                     uri: Optional[str] = None,
                     component_template_file: str = DEFAULT_COMPONENT_TEMPLATE_FILE):
    # create component folder with component name
    component_dir = os.path.join(infra_dir, TERRAFORM_DIR, name)
    io.create_dirs(component_dir)

    # render component.yaml
    uri = uri if uri else f'github.com/cloudposse/terraform-aws-components//modules/{name}?ref={{ .Version }}'
    template = jinja2.Environment(loader=FileSystemLoader(TEMPLATES_DIR)).get_template(component_template_file)
    component_content = template.render(name=name, uri=uri, version=version)
    io.save_string_to_file(os.path.join(component_dir, ATMOS_COMPONENT_FILE), component_content)


def prep_github_provider(config: Config):
    fake_github = mock.MagicMock()
    fake_github_provider = GitHubProvider(config, fake_github)
    fake_github_provider.branch_exists = mock.MagicMock(return_value=False)
    fake_github_provider.create_branch_and_push_all_changes = mock.MagicMock()
    return fake_github_provider


def test_no_version_specified(config: Config):
    # setup
    prepare_infra_repo(config.infra_repo_dir)
    create_component(config.infra_repo_dir, 'test_component', '')

    component_updater = ComponentUpdater(prep_github_provider(config), TERRAFORM_DIR, config)

    # test
    responses = component_updater.update()

    # validate
    assert len(responses) == 1
    assert responses[0].state == ComponentUpdaterResponseState.NO_VERSION_FOUND_IN_SOURCE_YAML


def test_not_valid_uri(config: Config):
    # setup
    prepare_infra_repo(config.infra_repo_dir)
    create_component(config.infra_repo_dir, 'test_component', '1.107.0', 'github.com/cloudposse/terraform-aws-components.git')

    component_updater = ComponentUpdater(prep_github_provider(config), TERRAFORM_DIR, config)

    # test
    responses = component_updater.update()

    # validate
    assert len(responses) == 1
    assert responses[0].state == ComponentUpdaterResponseState.NOT_VALID_URI_FOUND_IN_SOURCE_YAML


def test_components_repo_is_not_a_git_repo(config: Config):
    # setup
    config.components_download_dir = io.create_tmp_dir()
    prepare_infra_repo(config.infra_repo_dir)
    create_component(config.infra_repo_dir, 'test_component', '1.107.0', 'local//modules/component')

    component_updater = ComponentUpdater(prep_github_provider(config), TERRAFORM_DIR, config)

    # test
    responses = component_updater.update()

    # validate
    assert len(responses) == 1
    assert responses[0].state == ComponentUpdaterResponseState.URI_IS_NOT_GIT_REPO


def test_components_repo_git_no_tags(config: Config):
    # setup
    config.components_download_dir = TERRAFORM_COMPONENTS_INVALID_REPO_PATH
    prepare_infra_repo(config.infra_repo_dir)
    create_component(config.infra_repo_dir, 'test_component', '1.107.0')

    component_updater = ComponentUpdater(prep_github_provider(config), TERRAFORM_DIR, config)

    # test
    responses = component_updater.update()

    # validate
    assert len(responses) == 1
    assert responses[0].state == ComponentUpdaterResponseState.NO_LATEST_TAG_FOUND_IN_COMPONENT_REPO


def test_components_repo_already_up_to_date(config: Config):
    # setup
    prepare_infra_repo(config.infra_repo_dir)
    create_component(config.infra_repo_dir, 'test_component', EXISTING_TAG)

    component_updater = ComponentUpdater(prep_github_provider(config), TERRAFORM_DIR, config)

    # test
    responses = component_updater.update()

    # validate
    assert len(responses) == 1
    assert responses[0].state == ComponentUpdaterResponseState.ALREADY_UP_TO_DATE


def test_components_remote_branch_exists(config: Config):
    # setup
    prepare_infra_repo(config.infra_repo_dir)
    create_component(config.infra_repo_dir, 'test_component', '1.107.0')

    fake_github_provider = prep_github_provider(config)
    fake_github_provider.branch_exists = mock.MagicMock(return_value=True)
    component_updater = ComponentUpdater(fake_github_provider, TERRAFORM_DIR, config)

    # test
    responses = component_updater.update()

    # validate
    assert len(responses) == 1
    assert responses[0].state == ComponentUpdaterResponseState.REMOTE_BRANCH_FOR_COMPONENT_UPDATER_ALREADY_EXIST


def test_not_vendored_component_with_not_skip_vendoring(config: Config):
    # setup
    prepare_infra_repo(config.infra_repo_dir)
    create_component(config.infra_repo_dir, 'test_component', '1.107.0', os.getcwd() + '/src/tests/fixtures/terraform-aws-components//modules/test_component?ref={{ .Version }}')

    component_updater = ComponentUpdater(prep_github_provider(config), TERRAFORM_DIR, config)

    # test
    responses = component_updater.update()

    # validate
    assert len(responses) == 1

    response = responses[0]

    assert response.state == ComponentUpdaterResponseState.UPDATED

    # checking that component was vendored
    assert os.path.exists(os.path.join(response.component.infra_repo_dir, TERRAFORM_DIR, response.component.name, 'main.tf'))


def test_not_vendored_component_with_skip_vendoring(config: Config):
    # setup
    config.skip_component_vendoring = True

    prepare_infra_repo(config.infra_repo_dir)
    create_component(config.infra_repo_dir, 'test_component', '1.107.0', os.getcwd() + '/src/tests/fixtures/terraform-aws-components//modules/test_component?ref={{ .Version }}')

    component_updater = ComponentUpdater(prep_github_provider(config), TERRAFORM_DIR, config)

    # test
    responses = component_updater.update()

    # validate
    assert len(responses) == 1

    response = responses[0]

    assert response.state == ComponentUpdaterResponseState.UPDATED

    # checking that component was vendored
    assert not os.path.exists(os.path.join(response.component.infra_repo_dir, TERRAFORM_DIR, response.component.name, 'main.tf'))


def test_with_changes_found(config: Config):
    # setup
    prepare_infra_repo(config.infra_repo_dir)
    create_component(config.infra_repo_dir, 'test_component', '1.107.0', os.getcwd() + '/src/tests/fixtures/terraform-aws-components//modules/test_component?ref={{ .Version }}')

    component_updater = ComponentUpdater(prep_github_provider(config), TERRAFORM_DIR, config)

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
    create_component(config.infra_repo_dir, 'test_component', '1.107.0', os.getcwd() + '/src/tests/fixtures/terraform-aws-components//modules/test_component?ref={{ .Version }}')
    shutil.copyfile(os.getcwd() + '/src/tests/fixtures/terraform-aws-components/modules/test_component/main.tf',
                    os.path.join(config.infra_repo_dir, TERRAFORM_DIR, 'test_component', 'main.tf'))

    component_updater = ComponentUpdater(prep_github_provider(config), TERRAFORM_DIR, config)

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
    create_component(config.infra_repo_dir, 'test_component_01', '1.107.0', os.getcwd() + '/src/tests/fixtures/terraform-aws-components//modules/test_component?ref={{ .Version }}')
    create_component(config.infra_repo_dir, 'test_component_02', '1.107.0', os.getcwd() + '/src/tests/fixtures/terraform-aws-components//modules/test_component?ref={{ .Version }}')

    component_updater = ComponentUpdater(prep_github_provider(config), TERRAFORM_DIR, config)

    # test
    responses = component_updater.update()

    # validate
    assert len(responses) == 2
    assert responses[0].state == ComponentUpdaterResponseState.UPDATED
    assert responses[1].state == ComponentUpdaterResponseState.UPDATED


def test_missing_component(config: Config):
    # setup
    prepare_infra_repo(config.infra_repo_dir)
    create_component(config.infra_repo_dir, 'test_component', '1.107.0', os.getcwd() + '/src/tests/fixtures/terraform-aws-components//modules/missing_component?ref={{ .Version }}')

    component_updater = ComponentUpdater(prep_github_provider(config), TERRAFORM_DIR, config)

    # test
    responses = component_updater.update()

    # validate
    assert len(responses) == 1
    assert responses[0].state == ComponentUpdaterResponseState.FAILED_TO_VENDOR_COMPONENT


@pytest.mark.parametrize("include, exclude, expected_updated_components", [
    ('', '', ['test_component_01', 'test_component_02', 'test_component_03']),
    ('*', '', ['test_component_01', 'test_component_02', 'test_component_03']),
    ('test_component_*', '', ['test_component_01', 'test_component_02', 'test_component_03']),
    ('*component_*', '', ['test_component_01', 'test_component_02', 'test_component_03']),
    ('component_', '', []),
    ('test_component_*', '*04*', ['test_component_01', 'test_component_02', 'test_component_03']),
    ('test_component_*', '*02*', ['test_component_01', 'test_component_03']),
    ('', 'test*', []),
])
def test_include_and_exclude(config: Config, include: str, exclude: str, expected_updated_components: List[str]):
    # setup
    config.include = include
    config.exclude = exclude
    prepare_infra_repo(config.infra_repo_dir)
    create_component(config.infra_repo_dir, 'test_component_01', '1.107.0', os.getcwd() + '/src/tests/fixtures/terraform-aws-components//modules/test_component?ref={{ .Version }}')
    create_component(config.infra_repo_dir, 'test_component_02', '1.107.0', os.getcwd() + '/src/tests/fixtures/terraform-aws-components//modules/test_component?ref={{ .Version }}')
    create_component(config.infra_repo_dir, 'test_component_03', '1.107.0', os.getcwd() + '/src/tests/fixtures/terraform-aws-components//modules/test_component?ref={{ .Version }}')

    component_updater = ComponentUpdater(prep_github_provider(config), TERRAFORM_DIR, config)

    # test
    responses = component_updater.update()

    # validate
    assert len(responses) == len(expected_updated_components)
    names = [response.component.name for response in responses]
    assert sorted(names) == sorted(expected_updated_components)
