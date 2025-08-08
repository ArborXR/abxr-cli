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
    VERSIONS_LIST = "list"
    UPLOAD = "upload"
    RELEASE_CHANNELS_LIST = "release_channels"
    RELEASE_CHANNEL_DETAILS = "release_channel_details"
    APP_COMPATIBILITIES = "app_compatibilities"
    APP_COMPATIBILITY_DETAILS = "app_compatibility_details"

    
class SystemAppsService(ApiService):
    MAX_PARTS_PER_REQUEST = 4

    def __init__(self, base_url, token):
        base_url = base_url.split('/v2')[0]
        base_url = f'{base_url}/internal'

        super().__init__(base_url, token)

    def _initiate_upload(self, app_type, file_name, release_channel_id, app_compatibility_id):
        url = f'{self.base_url}/apps/{app_type}/versions'
        
        data = {'filename': file_name,
                'appCompatibilityId': app_compatibility_id
                }
        
        if release_channel_id:
            data['releaseChannelId'] = release_channel_id
        else:
            raise ValueError("release_channel_id must be provided.")

        response = requests.post(url, json=data, headers=self.headers)
        response.raise_for_status()
        
        return response.json()

    def _presigned_url(self, app_type, version_id, upload_id, key, part_numbers):
        url = f'{self.base_url}/apps/{app_type}/versions/{version_id}/pre-sign'
        data = {'key': key, 
                'uploadId': upload_id, 
                'partNumbers': part_numbers 
                }
        
        response = requests.post(url, json=data, headers=self.headers)
        response.raise_for_status()
        
        return response.json()

    def _complete_upload(self, app_type, version_id, upload_id, key, parts, version_name, release_notes):
        url = f'{self.base_url}/apps/{app_type}/versions/{version_id}/complete'
        data = {'key': key, 
                'uploadId': upload_id, 
                'parts': parts, 
                'versionName': version_name, 
                'releaseNotes': release_notes
                }
        
        response = requests.post(url, json=data, headers=self.headers)
        response.raise_for_status()
        
        return response.json()

    def upload_file(self, app_type, file_path, release_channel_name, app_compatibility_name, version_number, release_notes, silent):
        if release_channel_name is None:
            release_channel_name = 'Latest'
        
        app_compatibilities = self.get_all_app_compatibilities_for_app(app_type)
        app_compatibility_id = next((item['id'] for item in app_compatibilities if item['name'] == app_compatibility_name), None)
        if not app_compatibility_id:
            raise ValueError(f"App compatibility '{app_compatibility_name}' not found for app_type '{app_type}'.")

        # list all the release channels for the app type (filter by "Latest" or whatever passed in value)
        release_channel_id = None
        release_channels = self.get_all_release_channels_for_app(app_type)
        
        for release_channel in release_channels:
            if release_channel['name'] == release_channel_name:
                release_channel_detail = self.get_release_channel_detail(app_type, release_channel['id'])
                if release_channel_detail['version']['appCompatibility']['id'] == app_compatibility_id:
                    release_channel_id = release_channel_detail['id']

        if not release_channel_id:
            raise ValueError(f"Release channel not found for '{release_channel_name}' and app compatibility '{app_compatibility_name}'")
            
        
        file = MultipartFileS3(file_path)

        response = self._initiate_upload(app_type, file.file_name, release_channel_id, app_compatibility_id)

        upload_id = response['uploadId']
        key = response['key']
        version_id = response['versionId']

        part_numbers = list(range(1, file.get_part_numbers() + 1))

        uploaded_parts = []

        with tqdm(total=file.get_size(), unit='B', unit_scale=True, desc=f'Uploading {file.file_name}', disable=silent) as pbar:
            for i in range(0, len(part_numbers), self.MAX_PARTS_PER_REQUEST):
                part_numbers_slice = part_numbers[i:i + self.MAX_PARTS_PER_REQUEST]
                
                presigned_url_response = self._presigned_url(app_type, version_id, upload_id, key, part_numbers_slice)
                
                for item in presigned_url_response:
                    part_number = item['partNumber']
                    presigned_url = item['presignedUrl']

                    part = file.get_part(part_number)
                    response = requests.put(presigned_url, data=part)
                    response.raise_for_status()

                    uploaded_parts += [{'partNumber': part_number, 'eTag': response.headers['ETag']}]
                    pbar.update(len(part))
                
            complete_response = self._complete_upload(app_type, version_id, upload_id, key, uploaded_parts, version_number, release_notes)
            return complete_response
        
    def get_all_release_channels_for_app(self, app_type):
        url = f'{self.base_url}/apps/{app_type}/release-channels?per_page=20'

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
    
    def get_release_channel_detail(self, app_type, release_channel_id):
        url = f'{self.base_url}/apps/{app_type}/release-channels/{release_channel_id}'

        response = requests.get(url, headers=self.headers)
        response.raise_for_status()

        return response.json()
    
    def get_all_app_compatibilities_for_app(self, app_type):
        url = f'{self.base_url}/apps/{app_type}/app-compatibilities?per_page=20'

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
    
    def get_app_compatibility_detail(self, app_type, app_compatibility_id):
        url = f'{self.base_url}/apps/{app_type}/app-compatibilities/{app_compatibility_id}'

        response = requests.get(url, headers=self.headers)
        response.raise_for_status()

        return response.json()
    
    def get_all_app_versions_by_type(self, app_type):
        url = f'{self.base_url}/apps/{app_type}/versions?per_page=20'

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
    

class CommandHandler:
    def __init__(self, args):
        self.args = args
        self.service = SystemAppsService(self.args.url, self.args.token)

    def run(self):
        if self.args.system_apps_command == Commands.VERSIONS_LIST.value:
            app_versions = self.service.get_all_app_versions_by_type(self.args.app_type)

            if self.args.format == DataOutputFormats.JSON.value:
                print(json.dumps(app_versions))
            elif self.args.format == DataOutputFormats.YAML.value:
                print(yaml.dump(app_versions))
            else:
                print("Invalid output format.")

        elif self.args.system_apps_command == Commands.RELEASE_CHANNELS_LIST.value:
            release_channels = self.service.get_all_release_channels_for_app(self.args.app_type)

            if self.args.format == DataOutputFormats.JSON.value:
                print(json.dumps(release_channels))
            elif self.args.format == DataOutputFormats.YAML.value:
                print(yaml.dump(release_channels))
            else:
                print("Invalid output format.")

        elif self.args.system_apps_command == Commands.RELEASE_CHANNEL_DETAILS.value:
            release_channel_detail = self.service.get_release_channel_detail(self.args.app_type, self.args.release_channel_id)

            if self.args.format == DataOutputFormats.JSON.value:
                print(json.dumps(release_channel_detail))
            elif self.args.format == DataOutputFormats.YAML.value:
                print(yaml.dump(release_channel_detail))
            else:
                print("Invalid output format.")

        elif self.args.system_apps_command == Commands.APP_COMPATIBILITIES.value:
            app_compatibilities = self.service.get_all_app_compatibilities_for_app(self.args.app_type)

            if self.args.format == DataOutputFormats.JSON.value:
                print(json.dumps(app_compatibilities))
            elif self.args.format == DataOutputFormats.YAML.value:
                print(yaml.dump(app_compatibilities))
            else:
                print("Invalid output format.")

        elif self.args.system_apps_command == Commands.APP_COMPATIBILITY_DETAILS.value:
            app_compatibility_detail = self.service.get_app_compatibility_detail(self.args.app_type, self.args.app_compatibility_id)

            if self.args.format == DataOutputFormats.JSON.value:
                print(json.dumps(app_compatibility_detail))
            elif self.args.format == DataOutputFormats.YAML.value:
                print(yaml.dump(app_compatibility_detail))
            else:
                print("Invalid output format.")

        elif self.args.system_apps_command == Commands.UPLOAD.value:
            app_version = self.service.upload_file(self.args.app_type, self.args.filename, self.args.release_channel_name, self.args.app_compatibility_name, self.args.version_number, self.args.notes, self.args.silent)

            if self.args.format == DataOutputFormats.JSON.value:
                print(json.dumps(app_version))
            elif self.args.format == DataOutputFormats.YAML.value:
                print(yaml.dump(app_version))
            else:
                print("Invalid output format.")
