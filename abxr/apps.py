#!/usr/bin/env python3
#
# Copyright (c) 2024-2025 ABXR Labs, Inc.
# Released under the MIT License. See LICENSE file for details.
#

from tqdm import tqdm
import time
import zipfile
import tempfile
import shutil
import os

from enum import Enum

from abxr.api_service import ApiService
from abxr.constants import SYSTEM_FILES_TO_EXCLUDE, SYSTEM_DIRS_TO_EXCLUDE
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

    def _initiate_upload(self, app_id, file_name, app_build_type="standalone", release_channel_id=None, new_release_channel_title=None):
        url = f'{self.base_url}/apps/{app_id}/versions'
        data = {'filename': file_name}

        if app_build_type:
            data['appBuildType'] = app_build_type

        if release_channel_id:
            data['releaseChannelId'] = release_channel_id

        if new_release_channel_title:
            data['newReleaseChannelTitle'] = new_release_channel_title

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

    def upload_file(self, app_id, file_path, version_number, release_notes, silent, wait, max_wait_time_sec=60, app_build_type="standalone", release_channel_id=None, new_release_channel_title=None):
        file = MultipartFileS3(file_path)

        response = self._initiate_upload(app_id, file.file_name, app_build_type, release_channel_id, new_release_channel_title)

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

def _handle_zip_upload(args, apps_service):
    """Handle ZIP file upload by extracting and converting to bundle or regular upload

    Args:
        args: Command-line arguments
        apps_service: AppsService instance

    Returns:
        Upload response
    """
    zip_path = args.filename

    if not args.silent:
        print(f"Extracting ZIP file...")

    # Create temporary directory
    temp_dir = tempfile.mkdtemp(prefix='abxr_zip_')

    try:
        # Extract ZIP
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)

        # Find all APK files at root (case-insensitive, no subdirectories)
        apk_files = []
        for item in os.listdir(temp_dir):
            item_path = os.path.join(temp_dir, item)
            if os.path.isfile(item_path) and item.lower().endswith('.apk'):
                apk_files.append(item_path)

        # Validate APK count
        if len(apk_files) == 0:
            raise ValueError("No APK file found at root of ZIP")
        elif len(apk_files) > 1:
            raise ValueError(f"Multiple APK files found at root of ZIP ({len(apk_files)} APKs found)")

        apk_path = apk_files[0]

        # Find all other files (excluding system files)
        other_files = []
        for root, dirs, files in os.walk(temp_dir):
            # Skip system directories
            if any(sys_dir in root for sys_dir in SYSTEM_DIRS_TO_EXCLUDE):
                continue
            for file in files:
                file_path = os.path.join(root, file)
                # Skip if it's the APK or a system file
                if file_path != apk_path and file not in SYSTEM_FILES_TO_EXCLUDE:
                    other_files.append(file_path)

        # If only APK, use normal upload flow
        if not other_files:
            if not args.silent:
                print(f"ZIP contains only APK, using standard upload...")
            release_channel_id = getattr(args, 'release_channel_id', None)
            new_release_channel_title = getattr(args, 'new_release_channel_title', None)
            result = apps_service.upload_file(
                args.app_id,
                apk_path,
                args.version_number,
                args.notes,
                args.silent,
                args.wait,
                args.wait_time,
                release_channel_id=release_channel_id,
                new_release_channel_title=new_release_channel_title
            )
            return result

        # ZIP contains APK + other files - create bundle
        if not args.silent:
            print(f"ZIP contains APK and {len(other_files)} additional file(s), creating app bundle...")

        # Get app details to retrieve package name
        app_detail = apps_service.get_app_detail(args.app_id)
        package_name = app_detail.get('packageName')

        if not package_name:
            raise ValueError("Cannot create bundle from ZIP: app does not have a package name set. Upload an APK first to set the package name.")

        # Restructure: move OBB files to Android/obb/<package-name>/
        obb_dir = os.path.join(temp_dir, 'Android', 'obb', package_name)
        for file_path in other_files:
            if file_path.lower().endswith('.obb'):
                # Create OBB directory if needed
                os.makedirs(obb_dir, exist_ok=True)
                # Move OBB file
                file_name = os.path.basename(file_path)
                new_path = os.path.join(obb_dir, file_name)
                shutil.move(file_path, new_path)
                if not args.silent:
                    print(f"Moved {file_name} to Android/obb/{package_name}/")

        # Import AppBundlesService
        from abxr.app_bundles import AppBundlesService

        # Create bundle service
        bundle_service = AppBundlesService(args.url, args.token)

        # Upload as bundle
        release_channel_id = getattr(args, 'release_channel_id', None)
        new_release_channel_title = getattr(args, 'new_release_channel_title', None)
        result = bundle_service.upload_app_bundle(
            args.app_id,
            temp_dir,
            args.version_number,
            args.notes,
            args.silent,
            apk_path=apk_path,
            device_path=None,
            release_channel_id=release_channel_id,
            new_release_channel_title=new_release_channel_title
        )

        return result

    finally:
        # Clean up temp directory
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

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
            # Check if file is a ZIP - if so, extract and convert to bundle or regular upload
            if self.args.filename.lower().endswith('.zip'):
                app_version = _handle_zip_upload(self.args, self.service)
            else:
                release_channel_id = getattr(self.args, 'release_channel_id', None)
                new_release_channel_title = getattr(self.args, 'new_release_channel_title', None)
                app_version = self.service.upload_file(
                    self.args.app_id,
                    self.args.filename,
                    self.args.version_number,
                    self.args.notes,
                    self.args.silent,
                    self.args.wait,
                    self.args.wait_time,
                    release_channel_id=release_channel_id,
                    new_release_channel_title=new_release_channel_title
                )
            print_formatted(self.args.format, app_version)

        elif self.args.apps_command == Commands.SHARE.value:
            self.service.share_app(self.args.app_id, self.args.release_channel_id, self.args.organization_slug)

        elif self.args.apps_command == Commands.REVOKE_SHARE.value:
            self.service.revoke_shared_app(self.args.app_id, self.args.release_channel_id, self.args.organization_slug)
