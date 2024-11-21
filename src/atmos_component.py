import logging
import re
import os
from typing import Tuple
import yaml
import semver

from utils import io

VERSION_PATTERN = r"(?<=source:)(?<!mixins:)(.*?)(version:\s*v?\d+\.\d+\.\d+)"
# VERSION_PATTERN = r"version:\s*v?\d+\.\d+\.\d+"
URI_PATTERN = r"(?<=source:)(?<!mixins:)(.*?)(uri:\s*[^\n]*)"
COMPONENT_YAML = 'component.yaml'
README_EXTENTION = '.md'
MONOREPO_MAXIMUM_VERSION = '1.532.0'


class AtmosComponent:
    def __init__(self, infra_repo_dir: str, infra_terraform_dir: str, component_file: str):
        self.__infra_repo_dir = infra_repo_dir
        self.__infra_terraform_dir = infra_terraform_dir
        self.__component_file = component_file
        self.__content = ''
        self.__yaml_content = {}
        self.__initialize()

    @property
    def version(self):
        version = self.__yaml_content.get('spec', {}).get('source', {}).get('version')
        return version.strip().lstrip("v") if version else None

    @property
    def uri_repo(self) -> str:
        return self.__uri_repo

    @property
    def uri_path(self) -> str:
        return self.__uri_path

    @property
    def name(self) -> str:
        return self.__name

    @property
    def normalized_name(self) -> str:
        return self.__name.replace('/', '-')

    @property
    def relative_path(self) -> str:
        return self.__relative_path

    @property
    def infra_repo_dir(self) -> str:
        return self.__infra_repo_dir

    @property
    def infra_terraform_dir(self) -> str:
        return self.__infra_terraform_dir

    @property
    def component_file(self) -> str:
        return self.__component_file

    @property
    def component_dir(self) -> str:
        return os.path.dirname(self.__component_file)

    def __repr__(self):
        attributes = []

        for key, value in vars(self).items():
            if not key.endswith(('__content', '__yaml_content')):
                attributes.append(f"- {key}={value!r}")

        return "\n".join(attributes)

    def __initialize(self):
        self.__relative_path: str = os.path.relpath(self.__component_file, self.__infra_repo_dir)
        self.__name: str = self.__fetch_name()
        self.__content: str = self.__load_file()
        self.__yaml_content = self.__load_yaml_content()
        (self.__uri_repo, self.__uri_path) = self.__parse_uri()
        self.__migrate_new_org()

    def __migrate_new_org(self):
        if self.has_version() and semver.compare(self.version, MONOREPO_MAXIMUM_VERSION) != -1:
            self.migrate()

    def migrate(self):
        if (self.has_version() and
                self.has_valid_uri() and
                self.__uri_repo == 'github.com/cloudposse/terraform-aws-components.git'):
            component_name = '/'.join(self.__uri_path.split('/')[1:])
            config_path = os.path.join(os.path.dirname(__file__), "assets", "config.yaml")
            migration_config = yaml.load(io.read_file_to_string(config_path), Loader=yaml.FullLoader)
            prefix = migration_config.get('repo_settings').get('prefix')
            new_component_name = migration_config.get('component_map').get(component_name)
            if new_component_name:
                destination = new_component_name.replace('/', '-')
                self.__uri_repo = f"github.com/cloudposse-terraform-components/{prefix}-{destination}.git"
                self.__uri_path = "src"
                template = f"\g<1>uri: {self.__uri_repo}//{self.__uri_path}?ref={{{{ .Version }}}}"
                self.__content = re.sub(URI_PATTERN, template, self.__content, flags=re.DOTALL)
                self.__yaml_content = self.__load_yaml_content()

    def __fetch_name(self) -> str:
        return os.path.dirname(os.path.relpath(self.__component_file, os.path.join(self.__infra_repo_dir, self.__infra_terraform_dir)))

    def __load_file(self) -> str:
        return io.read_file_to_string(self.__component_file)

    def __parse_uri(self) -> Tuple[str, str]:
        uri = self.__yaml_content.get('spec', {}).get('source', {}).get('uri')

        if not uri:
            return None, None  # type: ignore

        uri_parts = uri.split('//')

        if len(uri_parts) < 2:
            return uri_parts[0], None  # type: ignore

        uri_repo = uri_parts[0]
        uri_path = uri_parts[1].split('?')[0]

        return uri_repo, uri_path

    def __load_yaml_content(self):
        return yaml.load(self.__content, Loader=yaml.FullLoader)

    def has_version(self) -> bool:
        try:
            return bool(semver.parse(self.version))
        except Exception:
            return False


    def has_valid_uri(self) -> bool:
        return bool(self.uri_repo and self.uri_path)

    def update_version(self, new_version: str):
        self.__content = re.sub(VERSION_PATTERN, f"\g<1>version: {new_version}", self.__content, flags=re.DOTALL)
        self.__yaml_content = self.__load_yaml_content()

    def persist(self, output_file=None):
        output_file = output_file if output_file else self.__component_file

        io.save_string_to_file(output_file, self.__content)
