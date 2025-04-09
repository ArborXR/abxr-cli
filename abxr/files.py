#!/usr/bin/env python3
#
# Copyright (c) 2024-2025 ABXR Labs, Inc.
# Released under the MIT License. See LICENSE file for details.
#

import requests
import yaml
import json
from tqdm import tqdm

from enum import Enum

from abxr.api_service import ApiService
from abxr.multipart import MultipartFileS3
from abxr.formats import DataOutputFormats

class Commands(Enum):
    LIST = "list"
    DETAILS = "details"
    UPLOAD = "upload"

class FilesService(ApiService):
    def __init__(self, base_url, token):
        super().__init__(base_url, token)

    def get_all_files(self):
        url = f'{self.base_url}/files?per_page=20'

        response = requests.get(url, headers=self.headers)
        response.raise_for_status()

        json = response.json()

        data = json['data']

        if json['links']:
            while json['links']['next']:
                response = requests.get(json['links']['next'], headers=self.headers)
                response.raise_for_status()
                json = response.json()

                data += json['data']

        return data
    
    def get_file_detail(self, file_id):
        url = f'{self.base_url}/files/{file_id}'

        response = requests.get(url, headers=self.headers)
        response.raise_for_status()

        return response.json()
    
class CommandHandler:
    def __init__(self, args):
        self.args = args
        self.service = FilesService(self.args.url, self.args.token)

    def run(self):
        if self.args.files_command == Commands.LIST.value:            
            files_list = self.service.get_all_files()

            if self.args.format == DataOutputFormats.JSON.value:
                print(json.dumps(files_list))
            elif self.args.format == DataOutputFormats.YAML.value:
                print(yaml.dump(files_list))
            else:
                print("Invalid output format.")

        elif self.args.files_command == Commands.DETAILS.value:
            file_detail = self.service.get_file_detail(self.args.file_id)

            if self.args.format == DataOutputFormats.JSON.value:
                print(json.dumps(file_detail))
            elif self.args.format == DataOutputFormats.YAML.value:
                print(yaml.dump(file_detail))
            else:
                print("Invalid output format.")

