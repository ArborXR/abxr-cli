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
    DEVICE_LIST = "list_for_device"
    DEVICE_ASSIGN = "assign_to_device"
    DEVICE_REMOVE = "remove_from_device"
    GROUP_ASSIGN = "assign_to_group"
    GROUP_REMOVE = "remove_from_group"

class FilesService(ApiService):
    def __init__(self, base_url, token):
        super().__init__(base_url, token)

    def _initiate_upload(self, file_name, device_path):
        url = f'{self.base_url}/files'
        data = {'filename': file_name,
                'path': device_path
                }
        
        response = requests.post(url, json=data, headers=self.headers)
        response.raise_for_status()
        
        return response.json()

    def _presigned_url(self, file_id, upload_id, key, part_numbers):
        url = f'{self.base_url}/files/{file_id}/pre-sign'
        data = {'key': key, 
                'uploadId': upload_id, 
                'partNumbers': part_numbers 
                }
        
        response = requests.post(url, json=data, headers=self.headers)
        response.raise_for_status()
        
        return response.json()

    def _complete_upload(self, file_id, upload_id, key, parts, conflict_strategy='replace'):
        url = f'{self.base_url}/files/{file_id}/complete'
        data = {'key': key, 
                'uploadId': upload_id, 
                'parts': parts, 
                'conflictStrategy': conflict_strategy
                }
        
        response = requests.post(url, json=data, headers=self.headers)
        response.raise_for_status()
        
        return response.json()

    def upload_file(self, file_path, device_path, silent):
        file = MultipartFileS3(file_path)

        response = self._initiate_upload(file.file_name, device_path)

        upload_id = response['uploadId']
        key = response['key']
        file_id = response['fileId']

        part_numbers = list(range(1, file.get_part_numbers() + 1))

        uploaded_parts = []

        with tqdm(total=file.get_size(), unit='B', unit_scale=True, desc=f'Uploading {file.file_name}', disable=silent) as pbar:
            for i in range(0, len(part_numbers), self.MAX_PARTS_PER_REQUEST):
                part_numbers_slice = part_numbers[i:i + self.MAX_PARTS_PER_REQUEST]
                
                presigned_url_response = self._presigned_url(file_id, upload_id, key, part_numbers_slice)
                
                for item in presigned_url_response:
                    part_number = item['partNumber']
                    presigned_url = item['presignedUrl']

                    part = file.get_part(part_number)
                    response = requests.put(presigned_url, data=part)
                    response.raise_for_status()

                    uploaded_parts += [{'partNumber': part_number, 'eTag': response.headers['ETag']}]
                    pbar.update(len(part))
                
            complete_response = self._complete_upload(file_id, upload_id, key, uploaded_parts)
            return complete_response

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
    
    def get_all_device_files(self, device_id):
        url = f'{self.base_url}/devices/{device_id}/files?per_page=20'

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
    
    def assign_file_to_device(self, file_id, device_id):
        url = f'{self.base_url}/devices/{device_id}/files'
        data = {'fileId': file_id }
        
        response = requests.post(url, json=data, headers=self.headers)
        response.raise_for_status()
        
        return response.json()

    def remove_file_from_device(self, file_id, device_id):
        url = f'{self.base_url}/devices/{device_id}/files'
        data = {'fileId': file_id }
        
        response = requests.delete(url, json=data, headers=self.headers)
        response.raise_for_status()
        
        return response.json()

    def assign_file_to_group(self, file_id, group_id):
        url = f'{self.base_url}/groups/{group_id}/files'
        data = { 'fileId': file_id }

        response = requests.post(url, json=data, headers=self.headers)
        response.raise_for_status()
        
        return response.json()

    def remove_file_from_group(self, file_id, group_id):
        url = f'{self.base_url}/groups/{group_id}/files'
        data = { 'fileId': file_id }

        response = requests.delete(url, json=data, headers=self.headers)
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

        elif self.args.files_command == Commands.UPLOAD.value:
            file = self.service.upload_file(self.args.filename, self.args.device_path, self.args.silent)

            if self.args.format == DataOutputFormats.JSON.value:
                print(json.dumps(file))
            elif self.args.format == DataOutputFormats.YAML.value:
                print(yaml.dump(file))
            else:
                print("Invalid output format.")

        elif self.args.files_command == Commands.DEVICE_LIST.value:
            device_files_list = self.service.get_all_device_files(self.args.device_id)
            
            if self.args.format == DataOutputFormats.JSON.value:
                print(json.dumps(device_files_list))
            elif self.args.format == DataOutputFormats.YAML.value:
                print(yaml.dump(device_files_list))
            else:
                print("Invalid output format.")

        elif self.args.files_command == Commands.DEVICE_ASSIGN.value:
            self.service.assign_file_to_device(self.args.file_id, self.args.device_id)

        elif self.args.files_command == Commands.DEVICE_REMOVE.value:
            self.service.remove_file_from_device(self.args.file_id, self.args.device_id)

        elif self.args.files_command == Commands.GROUP_ASSIGN.value:
            self.service.assign_file_to_group(self.args.file_id, self.args.group_id)

        elif self.args.files_command == Commands.GROUP_REMOVE.value:
            self.service.remove_file_from_group(self.args.file_id, self.args.group_id)

