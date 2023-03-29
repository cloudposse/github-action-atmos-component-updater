import os
import tempfile
import shutil
import glob
import hashlib


def save_string_to_file(file, string):
    with open(file, "w") as file:
        print(string, file=file)


def save_to_file(file, content):
    with open(file, "wb") as file:
        file.write(content)


def read_file_to_string(file):
    with open(file, 'r') as file:
        content = file.read()

    return content


def read_file_to_list_of_strings(file):
    with open(file, 'r') as file:
        result = file.read().splitlines()

    return result


def copy_dirs(src_dir, dst_dir):
    shutil.copytree(src_dir, dst_dir, dirs_exist_ok=True)


def create_tmp_dir():
    return tempfile.mkdtemp()


def create_dirs(dir):
    if not os.path.exists(dir):
        os.makedirs(dir)


def get_filenames_in_dir(dir, patterns):
    pattern = ' '.join([os.path.join(dir, pattern) for pattern in patterns])
    return glob.glob(pattern, recursive=True)


def remove_all_from_dir(dir):
    for filename in os.listdir(dir):
        file_path = os.path.join(dir, filename)

        if os.path.isfile(file_path) or os.path.islink(file_path):
            os.unlink(file_path)
        elif os.path.isdir(file_path):
            shutil.rmtree(file_path)


def calc_file_md5_hash(file):
    with open(file, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()
