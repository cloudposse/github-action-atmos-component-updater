import logging
from utils import io
import re
import os
import yaml

VERSION_PATTERN = r"version:\s*\d+\.\d+\.\d+"
COMPONENT_YAML = 'component.yaml'


class AtmosComponent:
    def __init__(self, infra_repo_dir: str, component_file: str):
        self.__infra_repo_dir = infra_repo_dir
        self.__component_file = component_file
        self.__initialize()
    
    def has_version(self):
        return self.get_version()

    def has_valid_uri(self):
        return self.get_uri_repo() and self.get_uri_path()

    def get_version(self):
        version = self.__yaml_content.get('spec', {}).get('source', {}).get('version')
        return version.strip() if version else None

    def get_uri_repo(self):
        return self.__uri_repo

    def get_uri_path(self):
        return self.__uri_path

    def get_name(self):
        return self.__name

    def get_relative_path(self):
        return self.__relative_path

    def get_infra_repo_dir(self):
        return self.__infra_repo_dir

    def get_component_file(self):
        return self.__component_file

    def get_component_dir(self):
        return os.path.dirname(self.__component_file)

    def __initialize(self):
        self.__name: str = self.__fetch_name()
        self.__content: str = self.__load_file()
        self.__yaml_content = self.__load_yaml_content()
        self.__relative_path: str = os.path.relpath(self.__component_file, self.__infra_repo_dir)
        (self.__uri_repo, self.__uri_path) = self.__parse_uri()

    def __fetch_name(self):
        return os.path.basename(os.path.dirname(self.__component_file))

    def __load_file(self):
        return io.read_file_to_string(self.__component_file)

    def __parse_uri(self):
        uri = self.__yaml_content.get('spec', {}).get('source', {}).get('uri')

        if not uri:
            return None, None

        uri_parts = uri.split('//')

        if len(uri_parts) < 2:
            return uri_parts[0], None

        uri_repo = uri_parts[0]
        uri_path = uri_parts[1].split('?')[0]

        return uri_repo, uri_path

    def __load_yaml_content(self):
        return yaml.load(self.__content, Loader=yaml.FullLoader)

    def update_version(self, new_version: str):
        self.__content = re.sub(VERSION_PATTERN, f"version: {new_version}", self.__content)
        self.__yaml_content = self.__load_yaml_content()

    def persist(self, output_file: str = None):
        output_file = output_file if output_file else self.__component_file

        io.save_string_to_file(output_file, self.__content)
