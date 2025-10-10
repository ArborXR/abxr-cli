#!/usr/bin/env python3
#
# Copyright (c) 2024-2025 ABXR Labs, Inc.
# Released under the MIT License. See LICENSE file for details.
#

from tqdm import tqdm
import time

from enum import Enum

from abxr.api_service import ApiService
from abxr.multipart import MultipartFileS3
from abxr.formats import DataOutputFormats
from abxr.output import print_formatted

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

    def _initiate_upload(self, app_id, file_name, app_bundle_name=None):
        url = f'{self.base_url}/apps/{app_id}/versions'
        data = {'filename': file_name}

        if app_bundle_name:
            data['appBundleName'] = app_bundle_name

        response = self.client.post(url, json=data, headers=self.headers)
        response.raise_for_status()

        return response.json()

    def _presigned_url(self, app_id, version_id, upload_id, key, part_numbers):
        url = f'{self.base_url}/apps/{app_id}/versions/{version_id}/pre-sign'
        data = {'key': key, 
                'uploadId': upload_id, 
                'partNumbers': part_numbers 
                }
        
        response = self.client.post(url, json=data, headers=self.headers)
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
        
        response = self.client.post(url, json=data, headers=self.headers)
        response.raise_for_status()
        
        return response.json()

    def upload_file(self, app_id, file_path, version_number, release_notes, silent, wait, max_wait_time_sec=60, app_bundle_name=None):
        file = MultipartFileS3(file_path)

        response = self._initiate_upload(app_id, file.file_name, app_bundle_name)

        upload_id = response['uploadId']
        key = response['key']
        version_id = response['versionId']
        app_bundle_id = response.get('appBundleId')  # Capture bundle ID if created

        part_numbers = list(range(1, file.get_part_numbers() + 1))

        uploaded_parts = []

        with tqdm(total=file.get_size(), unit='B', unit_scale=True, desc=f'Uploading {file.file_name}', disable=silent) as pbar:
            for i in range(0, len(part_numbers), self.MAX_PARTS_PER_REQUEST):
                part_numbers_slice = part_numbers[i:i + self.MAX_PARTS_PER_REQUEST]
                
                presigned_url_response = self._presigned_url(app_id, version_id, upload_id, key, part_numbers_slice)
                
                for item in presigned_url_response:
                    part_number = item['partNumber']
                    presigned_url = item['presignedUrl']

                    part = file.get_part(part_number)
                    response = self.client.put(presigned_url, data=part)
                    response.raise_for_status()

                    uploaded_parts += [{'partNumber': part_number, 'eTag': response.headers['ETag']}]
                    pbar.update(len(part))
                
            complete_response = self._complete_upload(app_id, version_id, upload_id, key, uploaded_parts, version_number, release_notes)

            total_time_sec = 0
            wait_indefinitely = max_wait_time_sec <= 0

            if wait_indefinitely:
                max_wait_time_sec = 1

            status = None

            if wait:
                while status != 'AVAILABLE' and total_time_sec < max_wait_time_sec:
                    versions = self.get_all_versions_for_app(app_id)
                    version = next((v for v in versions if v['id'] == version_id), None)
                    if version:
                        status = version['status']
                        if status == 'AVAILABLE':
                            break
                        elif status == 'FAILED':
                            raise Exception(f"Upload failed server processing for version {version_id} of app {app_id}.")
                    else:
                        raise Exception(f"Version {version_id} not found for uploaded app {app_id}.")
                    
                    pbar.set_description(f'Been waiting for upload to complete for {total_time_sec} seconds')
                    time.sleep(1)
                    total_time_sec += 1

                    if wait_indefinitely:
                        max_wait_time_sec += 1

            # Include appBundleId in response if it was created
            if app_bundle_id:
                complete_response['appBundleId'] = app_bundle_id

            return complete_response
        
    def get_all_apps(self):
        url = f'{self.base_url}/apps?per_page=20'

        response = self.client.get(url, headers=self.headers)
        response.raise_for_status()

        json = response.json()

        data = json['data']

        if json['links']:
            while json['links']['next']:
                response = self.client.get(json['links']['next'], headers=self.headers)
                response.raise_for_status()
                json = response.json()

                data += json['data']

        return data
    
    def get_app_detail(self, app_id):
        url = f'{self.base_url}/apps/{app_id}'

        response = self.client.get(url, headers=self.headers)
        response.raise_for_status()

        return response.json()
    
    def get_all_versions_for_app(self, app_id):
        url = f'{self.base_url}/apps/{app_id}/versions'

        response = self.client.get(url, headers=self.headers)
        response.raise_for_status()

        json = response.json()

        data = json['data']

        if json['links']:
            while json['links']['next']:
                response = self.client.get(json['links']['next'], headers=self.headers)
                response.raise_for_status()
                json = response.json()

                data += json['data']

        return data

    def get_versions_by_sha256(self, app_id, sha256_hashes):
        """Query app versions by SHA-256 hashes, return only AVAILABLE versions"""
        if not sha256_hashes:
            return []

        # Build query string with sha256[] array parameters
        query_params = '&'.join([f'sha256[]={hash}' for hash in sha256_hashes])
        url = f'{self.base_url}/apps/{app_id}/versions?{query_params}'

        response = self.client.get(url, headers=self.headers)
        response.raise_for_status()

        json_data = response.json()
        data = json_data.get('data', [])

        # Filter for AVAILABLE status only
        return [v for v in data if v.get('status') == 'AVAILABLE']

    def get_files_by_sha512(self, app_id, sha512_hashes):
        """Query app files by SHA-512 hashes"""
        if not sha512_hashes:
            return []

        # Build query string with sha512[] array parameters
        query_params = '&'.join([f'sha512[]={hash}' for hash in sha512_hashes])
        url = f'{self.base_url}/apps/{app_id}/files?{query_params}'

        response = self.client.get(url, headers=self.headers)
        response.raise_for_status()

        json_data = response.json()
        return json_data.get('data', [])

    def get_all_release_channels_for_app(self, app_id):
        url = f'{self.base_url}/apps/{app_id}/release-channels'

        response = self.client.get(url, headers=self.headers)
        response.raise_for_status()

        json = response.json()

        data = json['data']

        if json['links']:
            while json['links']['next']:
                response = self.client.get(json['links']['next'], headers=self.headers)
                response.raise_for_status()
                json = response.json()

                data += json['data']

        return data
    
    def get_release_channel_detail(self, app_id, release_channel_id):
        url = f'{self.base_url}/apps/{app_id}/release-channels/{release_channel_id}'

        response = self.client.get(url, headers=self.headers)
        response.raise_for_status()

        return response.json()
    
    def set_version_for_release_channel(self, app_id, release_channel_id, version_id):
        url = f'{self.base_url}/apps/{app_id}/release-channels/{release_channel_id}'

        data = {'versionId': version_id}

        response = self.client.put(url, json=data, headers=self.headers)
        response.raise_for_status()

        return response.json()
    
    def share_app(self, app_id, release_channel_id, organization_slug):
        url = f'{self.base_url}/apps/{app_id}/release-channels/{release_channel_id}/share'
        data = {'organizationSlug': organization_slug}

        response = self.client.post(url, json=data, headers=self.headers)
        response.raise_for_status()

        return response.json()
    
    def revoke_shared_app(self, app_id, release_channel_id, organization_slug):
        url = f'{self.base_url}/apps/{app_id}/release-channels/{release_channel_id}/share'
        data = {'organizationSlug': organization_slug}

        response = self.client.delete(url, json=data, headers=self.headers)
        response.raise_for_status()

        return response.json()

class CommandHandler:
    def __init__(self, args):
        self.args = args
        self.service = AppsService(self.args.url, self.args.token)

    def run(self):
        if self.args.apps_command == Commands.LIST.value:            
            apps_list = self.service.get_all_apps()
            print_formatted(self.args.format, apps_list)
            
        elif self.args.apps_command == Commands.DETAILS.value:
            app_detail = self.service.get_app_detail(self.args.app_id)
            print_formatted(self.args.format, app_detail)

        elif self.args.apps_command == Commands.RELEASE_CHANNELS_LIST.value:
            release_channels = self.service.get_all_release_channels_for_app(self.args.app_id)
            print_formatted(self.args.format, release_channels)

        elif self.args.apps_command == Commands.RELEASE_CHANNEL_DETAILS.value:
            release_channel_detail = self.service.get_release_channel_detail(self.args.app_id, self.args.release_channel_id)
            print_formatted(self.args.format, release_channel_detail)

        elif self.args.apps_command == Commands.VERSION_LIST.value:
            versions = self.service.get_all_versions_for_app(self.args.app_id)
            print_formatted(self.args.format, versions)

        elif self.args.apps_command == Commands.RELEASE_CHANNEL_SET_VERSION.value:
            self.service.set_version_for_release_channel(self.args.app_id, self.args.release_channel_id, self.args.version_id)

        elif self.args.apps_command == Commands.UPLOAD.value:
            # Check if bundle upload is requested
            if hasattr(self.args, 'bundle_directory') and self.args.bundle_directory:
                # Validate bundle-name is provided
                if not hasattr(self.args, 'bundle_name') or not self.args.bundle_name:
                    raise ValueError("--bundle-name is required when using --bundle-directory")

                # Call bundle upload with apk_path
                from abxr.app_bundles import AppBundlesService
                bundle_service = AppBundlesService(self.args.url, self.args.token)
                result = bundle_service.upload_app_bundle(
                    self.args.app_id,
                    self.args.bundle_directory,  # folder with bundle files
                    self.args.bundle_name,
                    self.args.version_number,
                    self.args.notes,
                    self.args.silent,
                    apk_path=self.args.filename  # APK path provided separately
                )
                print_formatted(self.args.format, result)
            else:
                # Normal APK-only upload (existing behavior)
                app_version = self.service.upload_file(self.args.app_id, self.args.filename, self.args.version_number, self.args.notes, self.args.silent, self.args.wait, self.args.wait_time)
                print_formatted(self.args.format, app_version)

        elif self.args.apps_command == Commands.SHARE.value:
            self.service.share_app(self.args.app_id, self.args.release_channel_id, self.args.organization_slug)

        elif self.args.apps_command == Commands.REVOKE_SHARE.value:
            self.service.revoke_shared_app(self.args.app_id, self.args.release_channel_id, self.args.organization_slug)
