import json
import os
import tempfile
import shutil
import glob
import hashlib


def save_string_to_file(file, string):
    with open(file, "w", encoding="utf-8") as file:
        print(string, file=file)


def save_to_file(file, content):
    with open(file, "wb", encoding="utf-8") as file:
        file.write(content)


def read_file_to_string(file):
    with open(file, 'r', encoding="utf-8") as file:
        content = file.read()

    return content


def read_file_to_list_of_strings(file):
    with open(file, 'r', encoding="utf-8") as file:
        result = file.read().splitlines()

    return result


def copy_dirs(src_dir, dst_dir):
    shutil.copytree(src_dir, dst_dir, dirs_exist_ok=True)


def create_tmp_dir():
    return tempfile.mkdtemp()


def create_dirs(dir_path: str):
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)


def get_filenames_in_dir(dir_path: str, patterns):
    pattern = ' '.join([os.path.join(dir_path, pattern) for pattern in patterns])
    return glob.glob(pattern, recursive=True)


def calc_file_md5_hash(file):
    with open(file, "rb") as file:
        return hashlib.md5(file.read()).hexdigest()


def append_line_to_file(file_name, line):
    with open(file_name, "a", encoding="utf-8") as file:
        print(line, file=file)


def serialize_to_json_file(file_path, data, indent=4):
    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=indent)
