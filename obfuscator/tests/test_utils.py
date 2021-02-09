import os
import shutil
import unittest
from tempfile import mkstemp

from strategy import utils


class TestUtils(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        dir_name = os.path.dirname(__file__)
        self.test_logs_dir = f"{dir_name}/logs_dir"
        self.a1_folder = f"{dir_name}/logs_dir/a1"
        self.b_folder = f"{dir_name}/logs_dir/a1/b"
        self.a2_folder = f"{dir_name}/logs_dir/a2"

    def test__get_size(self):
        x = utils.get_file_size(self.get_single_text_file())
        self.assertEqual(type(x), tuple)
        self.assertEqual(len(x), 2)
        self.assertEqual(type(x[0]), int)
        self.assertEqual(type(x[1]), str)
        self.assertEqual(x, (78, "78.00 bytes"))

    def test__get_lines_number(self):
        x = utils.get_lines_number(self.get_single_text_file())
        self.assertEqual(type(x), int)
        self.assertEqual(x, 9)

    def test__get_folders_difference(self):
        a2_file = self.get_text_files(logs_dir=self.a2_folder)[0]
        new_folder_name = None
        try:
            new_folder_name = utils.get_folders_difference(filename=a2_file, folder=self.a1_folder)
            self.assertEqual(new_folder_name, os.path.join(self.test_logs_dir, "a1", "a2"))
            self.assertTrue(os.path.exists(new_folder_name))
        finally:
            if new_folder_name:
                shutil.rmtree(new_folder_name)

    def test__clone_file(self):
        new_file = os.path.join(self.a2_folder, "example.txt")
        new_file_abs = utils.clone_file_path(filename=new_file, target_dir=self.b_folder, suffix="__new")
        try:
            self.assertEqual(new_file_abs, os.path.join(self.test_logs_dir, "a1", "b", "a2", "example.txt__new"))
        finally:
            shutil.rmtree(os.path.join(self.b_folder, "a2"))

    def _test__split_file(self):
        f = self.get_single_text_file()
        file_parts = []
        num_parts = 3
        try:
            file_parts = utils.split_file(path=f, num_parts=num_parts, output_folder=self.a2_folder)
            self.assertEqual(len(file_parts), num_parts)
            for p in file_parts:
                self.assertTrue(utils.PART_SUFFIX in p)
        finally:
            for f in file_parts:
                os.remove(f)

    def _test__combine_files(self):
        text_file = self.get_single_text_file()
        output_file = os.path.join(self.a2_folder, "combined")
        file_parts = []
        new_files = []
        num_parts = 3
        try:
            file_parts = utils.split_file(path=text_file, num_parts=num_parts, output_folder=self.a2_folder)
            for idx, part_file in enumerate(file_parts):
                prefix = f"{os.path.basename(part_file)}{utils.FILE_PREFIX}"
                new_folder_name = utils.get_folders_difference(filename=part_file, folder=self.a2_folder)
                tmp_fd, abs_tmp_path = mkstemp(dir=new_folder_name, text=True, prefix=prefix, suffix=utils.NEW_FILE_SUFFIX)
                new_files.append(abs_tmp_path)

            new_files = sorted(new_files, key=utils.sort_func)

            # check sort
            for idx, f in enumerate(new_files):
                self.assertEqual(int(f.split(utils.FILE_PREFIX)[-3]), idx)

            utils.combine_files(files=file_parts, output_file=output_file)
            self.assertEqual(utils.get_file_size(output_file), utils.get_file_size(text_file))
        finally:
            for f in new_files + file_parts + [output_file]:
                try:
                    os.remove(f)
                except:
                    pass

    def test__get_txt_files(self):
        # must be last test
        text_files = self.get_text_files()
        self.assertEqual(len(text_files), 4)
        self.assertIn(os.path.join(self.test_logs_dir, "regular.log"), text_files)
        self.assertIn(os.path.join(self.a2_folder, "file_in_a2"), text_files)

    # Privates
    def get_single_text_file(self):
        args = Dummy()
        args.ignore_hint = "-NoObf4Me-"
        args.input_folder = self.test_logs_dir
        return utils.get_txt_files(args)[0]

    def get_text_files(self, logs_dir=None):
        args = Dummy()
        args.ignore_hint = "-NoObf4Me-"
        args.input_folder = logs_dir or self.test_logs_dir
        return utils.get_txt_files(args)


class Dummy:
    pass