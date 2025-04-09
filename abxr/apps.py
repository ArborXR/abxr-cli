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
    VERSION_LIST = "versions"
    RELEASE_CHANNELS_LIST = "release_channels"
    RELEASE_CHANNEL_DETAILS = "release_channel_details"
    RELEASE_CHANNEL_SET_VERSION = "release_channel_set_version"
    UPLOAD = "upload"
    SHARE = "share"
    REVOKE_SHARE = "revoke"

class AppsService(ApiService):
    MAX_PARTS_PER_REQUEST = 4

    def __init__(self, base_url, token):
        super().__init__(base_url, token)

    def _initiate_upload(self, app_id, file_name):
        url = f'{self.base_url}/apps/{app_id}/versions'
        data = {'filename': file_name}
        
        response = requests.post(url, json=data, headers=self.headers)
        response.raise_for_status()
        
        return response.json()

    def _presigned_url(self, app_id, version_id, upload_id, key, part_numbers):
        url = f'{self.base_url}/apps/{app_id}/versions/{version_id}/pre-sign'
        data = {'key': key, 
                'uploadId': upload_id, 
                'partNumbers': part_numbers 
                }
        
        response = requests.post(url, json=data, headers=self.headers)
        response.raise_for_status()
        
        return response.json()

    def _complete_upload(self, app_id, version_id, upload_id, key, parts, version_name, release_notes):
        url = f'{self.base_url}/apps/{app_id}/versions/{version_id}/complete'
        data = {'key': key, 
                'uploadId': upload_id, 
                'parts': parts, 
                'versionName': version_name, 
                'releaseNotes': release_notes
                }
        
        response = requests.post(url, json=data, headers=self.headers)
        response.raise_for_status()
        
        return response.json()

    def upload_file(self, app_id, file_path, version, release_notes):
        print(f"Uploading {file_path} to app_id {app_id}...")

        file = MultipartFileS3(file_path)

        response = self._initiate_upload(app_id, file.file_name)

        upload_id = response['uploadId']
        key = response['key']
        version_id = response['versionId']

        part_numbers = list(range(1, file.get_part_numbers() + 1))

        uploaded_parts = []

        with tqdm(total=file.get_size(), unit='B', unit_scale=True, desc=f'Uploading {file.file_name}') as pbar:
            for i in range(0, len(part_numbers), self.MAX_PARTS_PER_REQUEST):
                part_numbers_slice = part_numbers[i:i + self.MAX_PARTS_PER_REQUEST]
                
                presigned_url_response = self._presigned_url(app_id, version_id, upload_id, key, part_numbers_slice)
                
                for item in presigned_url_response:
                    part_number = item['partNumber']
                    presigned_url = item['presignedUrl']

                    part = file.get_part(part_number)
                    response = requests.put(presigned_url, data=part)
                    response.raise_for_status()

                    uploaded_parts += [{'partNumber': part_number, 'eTag': response.headers['ETag']}]
                    pbar.update(len(part))
                
            complete_response = self._complete_upload(app_id, version_id, upload_id, key, uploaded_parts, version, release_notes)
            return complete_response
        
    def get_all_apps(self):
        url = f'{self.base_url}/apps?per_page=20'

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
    
    def get_app_detail(self, app_id):
        url = f'{self.base_url}/apps/{app_id}'

        response = requests.get(url, headers=self.headers)
        response.raise_for_status()

        return response.json()
    
    def get_all_versions_for_app(self, app_id):
        url = f'{self.base_url}/apps/{app_id}/versions'

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
    
    def get_all_release_channels_for_app(self, app_id):
        url = f'{self.base_url}/apps/{app_id}/release-channels'

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
    
    def get_release_channel_detail(self, app_id, release_channel_id):
        url = f'{self.base_url}/apps/{app_id}/release-channels/{release_channel_id}'

        response = requests.get(url, headers=self.headers)
        response.raise_for_status()

        return response.json()
    
    def set_version_for_release_channel(self, app_id, release_channel_id, version_id):
        url = f'{self.base_url}/apps/{app_id}/release-channels/{release_channel_id}'

        data = {'versionId': version_id}

        response = requests.put(url, json=data, headers=self.headers)
        response.raise_for_status()

        return response.json()
    
    def share_app(self, app_id, release_channel_id, organization_slug):
        print(f"Sharing app_id {app_id} with release channel {release_channel_id} to org {organization_slug}...")

        url = f'{self.base_url}/apps/{app_id}/release-channels/{release_channel_id}/share'
        data = {'organizationSlug': organization_slug}

        response = requests.post(url, json=data, headers=self.headers)
        response.raise_for_status()

        return response.json()
    
    def revoke_shared_app(self, app_id, release_channel_id, organization_slug):
        print(f"Revoking Share of app_id {app_id} with release channel {release_channel_id} to org {organization_slug}...")

        url = f'{self.base_url}/apps/{app_id}/release-channels/{release_channel_id}/share'
        data = {'organizationSlug': organization_slug}

        response = requests.delete(url, json=data, headers=self.headers)
        response.raise_for_status()

        return response.json()

class CommandHandler:
    def __init__(self, args):
        self.args = args
        self.service = AppsService(self.args.url, self.args.token)

    def run(self):
        if self.args.apps_command == Commands.LIST.value:            
            apps_list = self.service.get_all_apps()

            if self.args.format == DataOutputFormats.JSON.value:
                print(json.dumps(apps_list))
            elif self.args.format == DataOutputFormats.YAML.value:
                print(yaml.dump(apps_list))
            else:
                print("Invalid output format.")

        elif self.args.apps_command == Commands.DETAILS.value:
            app_detail = self.service.get_app_detail(self.args.app_id)

            if self.args.format == DataOutputFormats.JSON.value:
                print(json.dumps(app_detail))
            elif self.args.format == DataOutputFormats.YAML.value:
                print(yaml.dump(app_detail))
            else:
                print("Invalid output format.")

        elif self.args.apps_command == Commands.RELEASE_CHANNELS_LIST.value:
            release_channels = self.service.get_all_release_channels_for_app(self.args.app_id)

            if self.args.format == DataOutputFormats.JSON.value:
                print(json.dumps(release_channels))
            elif self.args.format == DataOutputFormats.YAML.value:
                print(yaml.dump(release_channels))
            else:
                print("Invalid output format.")

        elif self.args.apps_command == Commands.RELEASE_CHANNEL_DETAILS.value:
            release_channel_detail = self.service.get_release_channel_detail(self.args.app_id, self.args.release_channel_id)

            if self.args.format == DataOutputFormats.JSON.value:
                print(json.dumps(release_channel_detail))
            elif self.args.format == DataOutputFormats.YAML.value:
                print(yaml.dump(release_channel_detail))
            else:
                print("Invalid output format.")

        elif self.args.apps_command == Commands.VERSION_LIST.value:
            versions = self.service.get_all_versions_for_app(self.args.app_id)

            if self.args.format == DataOutputFormats.JSON.value:
                print(json.dumps(versions))
            elif self.args.format == DataOutputFormats.YAML.value:
                print(yaml.dump(versions))
            else:
                print("Invalid output format.")

        elif self.args.apps_command == Commands.RELEASE_CHANNEL_SET_VERSION.value:
            self.service.set_version_for_release_channel(self.args.app_id, self.args.release_channel_id, self.args.version_id)

        elif self.args.apps_command == Commands.UPLOAD.value:
            self.service.upload_file(self.args.app_id, self.args.filename, self.args.version, self.args.notes)

        elif self.args.apps_command == Commands.SHARE.value:
            self.service.share_app(self.args.app_id, self.args.release_channel_id, self.args.organization_slug)

        elif self.args.apps_command == Commands.REVOKE_SHARE.value:
            self.service.revoke_shared_app(self.args.app_id, self.args.release_channel_id, self.args.organization_slug)
