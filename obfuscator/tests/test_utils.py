import os
import shutil
from tempfile import mkstemp

from ..lib import utils


dir_name = os.path.dirname(__file__)
test_logs_dir = f"{dir_name}/logs_dir"
a1_folder = f"{dir_name}/logs_dir/folder1"
b_folder = f"{dir_name}/logs_dir/folder1/b"
a_folder = f"{dir_name}/logs_dir/a"

for fl in (test_logs_dir, a1_folder, b_folder, a_folder):
    assert os.path.exists(fl), f"file not exist: {fl}"


def test_get_size():
    x = utils.get_file_size(get_single_text_file())
    assert isinstance(x, tuple)
    assert len(x) == 2
    assert isinstance(x[0], int)
    assert isinstance(x[1], str)


def test_get_lines_number():
    x = utils.get_lines_number(get_single_text_file())
    assert isinstance(x, int)


def test_get_folders_difference():
    a2_file = _get_text_files(a_folder)[0]
    new_folder_name = None
    try:
        new_folder_name = utils.get_folders_difference(filename=a2_file, folder=a1_folder)
        assert new_folder_name == os.path.join(test_logs_dir, "folder1", "a")
        assert os.path.exists(new_folder_name)
    finally:
        if new_folder_name:
            shutil.rmtree(new_folder_name)


def test_clone_file():
    new_file = os.path.join(a_folder, "example.txt")
    new_file_abs = utils.clone_file_path(filename=new_file, target_dir=b_folder, suffix="__new")
    try:
        assert new_file_abs == os.path.join(test_logs_dir, "folder1", "b", "a", "example.txt__new")
    finally:
        shutil.rmtree(os.path.join(b_folder, "a"))


def test_split_file():
    f = get_single_text_file()
    file_parts = []
    num_parts = 2
    try:
        file_parts = utils.split_file(path=f, num_parts=num_parts, output_folder=a_folder)
        assert len(file_parts) == num_parts
        for p in file_parts:
            assert utils.PART_SUFFIX in p
    finally:
        for f in file_parts:
            os.remove(f)


def test_combine_files():
    text_file = get_single_text_file()
    output_file = os.path.join(a_folder, "combined")
    file_parts = []
    new_files = []
    num_parts = 3
    try:
        file_parts = utils.split_file(path=text_file, num_parts=num_parts, output_folder=a_folder)
        for idx, part_file in enumerate(file_parts):
            prefix = f"{os.path.basename(part_file)}{utils.FILE_PREFIX}"
            new_folder_name = utils.get_folders_difference(filename=part_file, folder=a_folder)
            tmp_fd, abs_tmp_path = mkstemp(
                dir=new_folder_name,
                text=True,
                prefix=prefix,
                suffix=utils.NEW_FILE_SUFFIX,
            )
            new_files.append(abs_tmp_path)

        new_files = sorted(new_files, key=utils.sort_split_file_func)

        # check sort
        for idx, f in enumerate(new_files):
            assert int(f.split(utils.FILE_PREFIX)[-3]) == idx

        utils.combine_files(files=file_parts, output_file=output_file)
        assert utils.get_file_size(output_file) == utils.get_file_size(text_file)
    finally:
        for f in [*new_files, *file_parts, output_file]:
            try:
                os.remove(f)
            except OSError:
                pass


def test_get_txt_files():
    # must be last test
    text_files = _get_text_files()
    assert os.path.join(test_logs_dir, "regular.log") in text_files
    assert os.path.join(a_folder, "file_in_a") in text_files
    assert os.path.join(b_folder, "file_in_b.log") in text_files


# Privates
def get_single_text_file():
    args = Dummy()
    args.ignore_hint = "-NoObf4Me-"
    args.input_folder = test_logs_dir
    return utils.get_text_files(args)[0]


def _get_text_files(logs_dir=test_logs_dir):
    args = Dummy()
    args.ignore_hint = "-NoObf4Me-"
    args.input_folder = logs_dir
    return utils.get_text_files(args)


class Dummy:
    pass
