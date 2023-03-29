from utils import io
import re
import os
import yaml

VERSION_PATTERN = r"version:\s*\d+\.\d+\.\d+"
COMPONENT_YAML = 'component.yaml'


class AtmosComponent:
    def __init__(self, infra_repo_dir, component_file: str):
        self.__component_file = component_file
        self.__infra_repo_dir = infra_repo_dir
        self.__initialize()

    def get_version(self):
        version = self.__yaml_content.get('spec', {}).get('source', {}).get('version')
        return version.strip() if version else None

    def get_name(self):
        return self.__name

    def get_component_dir(self):
        return self.__component_dir

    def get_relative_path(self):
        return self.__relative_path

    def get_relative_dir(self):
        return self.__relative_dir

    def get_infra_repo_dir(self):
        return self.__infra_repo_dir

    def __initialize(self):
        self.__name = self.__fetch_name()
        self.__content = self.__load_file()
        self.__yaml_content = self.__load_yaml_content()
        self.__relative_path = os.path.relpath(self.__component_file, self.__infra_repo_dir)
        self.__relative_dir = os.path.dirname(self.__relative_path)
        self.__component_dir = os.path.dirname(self.__component_file)

    def __fetch_name(self):
        return os.path.basename(os.path.dirname(self.__component_file))

    def __load_file(self):
        return io.read_file_to_string(self.__component_file)

    def __load_yaml_content(self):
        return yaml.load(self.__content, Loader=yaml.FullLoader)

    def update_version(self, new_version: str):
        self.__content = re.sub(VERSION_PATTERN, f"version: {new_version}", self.__content)
        self.__yaml_content = self.__load_yaml_content()

    def persist(self, output_file: str = None):
        output_file = output_file if output_file else self.__component_file

        io.save_string_to_file(output_file, self.__content)
