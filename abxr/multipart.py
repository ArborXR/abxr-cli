#
# Copyright (c) 2024-2025 ABXR Labs, Inc.
# Released under the MIT License. See LICENSE file for details.
#

import os

class MultipartFileS3:
    MAX_PARTS = 1000
    MIN_PART_SIZE = 5 * 1024 * 1024
    MAX_PART_SIZE = 5 * 1024 * 1024 * 1024

    def __init__(self, file_path):
        self.file_path = file_path
        self.file_name = file_path.split('/')[-1]
        self.size = self.get_size()
        self.part_size = self.get_part_size()
        self.part_numbers = self.get_part_numbers()

    def get_size(self):
        return os.path.getsize(self.file_path)

    def get_part_size(self):
        part_size = self.size // self.MAX_PARTS
        return max(min(part_size, self.MAX_PART_SIZE), self.MIN_PART_SIZE)

    def get_part_numbers(self):
        return self.size // self.part_size + (1 if self.size % self.part_size > 0 else 0)

    def get_part(self, part_number):
        part_index = part_number - 1
        with open(self.file_path, 'rb') as file:
            file.seek(part_index * self.part_size)
            return file.read(self.part_size)