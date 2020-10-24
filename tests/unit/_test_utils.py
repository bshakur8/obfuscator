import os
import shutil
import unittest

from src import utils
from pathlib import Path
base_dir = f"{str(Path(__file__).parent.parent)}"


class TestUtils(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.test_logs_dir = os.path.join(base_dir, 'logs_dir')
        self.a1_folder = f"{self.test_logs_dir}/a1"
        self.b_folder = f"{self.a1_folder}/b"
        self.a2_folder = f"{self.test_logs_dir}/a2"

    def test__get_size(self):
        x = utils.get_size(self.get_single_text_file())
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
        new_file_abs = utils.clone_file(filename=new_file, target_dir=self.b_folder, suffix="__new")
        try:
            self.assertEqual(new_file_abs, os.path.join(self.test_logs_dir, "a1", "b", "a2", "example.txt__new"))
        finally:
            shutil.rmtree(os.path.join(self.b_folder, "a2"))

    def test__split_file(self):
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

    def test__combine_files(self):
        f = self.get_single_text_file()
        output_file = os.path.join(self.a2_folder, "combined")

        file_parts = []
        num_parts = 3
        try:
            file_parts = utils.split_file(path=f, num_parts=num_parts, output_folder=self.a2_folder)
            utils.combine_files(list_files=file_parts, output_file=output_file)
            self.assertEqual(utils.get_size(output_file), utils.get_size(f))
        finally:
            for f in file_parts + [output_file]:
                os.remove(f)

    def test__get_txt_files(self):
        # must be last test
        text_files = self.get_text_files()
        self.assertEqual(len(text_files), 2)
        self.assertIn(os.path.join(self.test_logs_dir, "regular.log"), text_files)
        self.assertIn(os.path.join(self.a2_folder, "file_in_a2"), text_files)

    # Privates
    def get_single_text_file(self):
        return utils.get_txt_files(logs_dir=self.test_logs_dir, ignore_hint="-NoObf4Me-")[0]

    def get_text_files(self, logs_dir=None):
        logs_dir = logs_dir or self.test_logs_dir
        return utils.get_txt_files(logs_dir=logs_dir, ignore_hint="-NoObf4Me-")
