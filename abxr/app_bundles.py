#!/usr/bin/env python3
#
# Copyright (c) 2024-2025 ABXR Labs, Inc.
# Released under the MIT License. See LICENSE file for details.
#

import os
import hashlib
from tqdm import tqdm
import time
from pathlib import Path

from enum import Enum

from abxr.api_service import ApiService
from abxr.multipart import MultipartFileS3
from abxr.formats import DataOutputFormats
from abxr.output import print_formatted

class Commands(Enum):
    LIST = "list"             # List app bundles for an app
    DETAILS = "details"       # Get details of a specific app bundle
    UPLOAD = "upload"         # Upload a new bundle version
    ADD_FILES = "add_files"   # Add files to an app bundle
    FINALIZE = "finalize"     # Finalize an app bundle

class AppBundlesService(ApiService):
    MAX_PARTS_PER_REQUEST = 4

    def __init__(self, base_url, token):
        super().__init__(base_url, token)

    def calculate_sha256(self, file_path):
        """Calculate SHA-256 hash of a file (for builds)"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def calculate_sha512(self, file_path):
        """Calculate SHA-512 hash of a file (for bundle files)"""
        sha512_hash = hashlib.sha512()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha512_hash.update(byte_block)
        return sha512_hash.hexdigest()

    def get_all_app_bundles_for_app(self, app_id, status=None):
        """Get all app bundles for a specific app"""
        url = f'{self.base_url}/apps/{app_id}/app-bundles?per_page=20'
        
        if status:
            url += f'&status={status}'

        response = self.client.get(url, headers=self.headers)
        response.raise_for_status()

        json_data = response.json()
        data = json_data['data']

        if json_data.get('links') and 'next' in json_data['links']:
            while json_data['links']['next']:
                response = self.client.get(json_data['links']['next'], headers=self.headers)
                response.raise_for_status()
                json_data = response.json()
                data += json_data['data']

        return data
    
    def get_app_bundle_detail(self, app_bundle_id):
        """Get details of a specific app bundle"""
        url = f'{self.base_url}/app-bundles/{app_bundle_id}'

        response = self.client.get(url, headers=self.headers)
        response.raise_for_status()

        return response.json()
    
    def get_all_files_for_app_bundle(self, app_bundle_id):
        """Get all files associated with an app bundle"""
        url = f'{self.base_url}/app-bundles/{app_bundle_id}/files?per_page=20'

        response = self.client.get(url, headers=self.headers)
        response.raise_for_status()

        json_data = response.json()
        data = json_data['data']

        if json_data.get('links') and 'next' in json_data['links']:
            while json_data['links']['next']:
                response = self.client.get(json_data['links']['next'], headers=self.headers)
                response.raise_for_status()
                json_data = response.json()
                data += json_data['data']

        return data
    
    def get_all_bundled_files_for_app(self, app_id):
        """Get all bundled files for an app"""
        url = f'{self.base_url}/apps/{app_id}/files?per_page=20'

        response = self.client.get(url, headers=self.headers)
        response.raise_for_status()

        json_data = response.json()
        data = json_data['data']

        if json_data.get('links') and 'next' in json_data['links']:
            while json_data['links']['next']:
                response = self.client.get(json_data['links']['next'], headers=self.headers)
                response.raise_for_status()
                json_data = response.json()
                data += json_data['data']

        return data
    
    
    def add_files_to_app_bundle(self, app_bundle_id, files):
        """Add files to an existing app bundle
        
        files should be a list of dictionaries with keys:
        - fileId: The ID of the file
        - path: (optional) The path where the file should be placed
        """
        url = f'{self.base_url}/app-bundles/{app_bundle_id}/files'
        
        data = {'files': files}

        response = self.client.post(url, json=data, headers=self.headers)
        response.raise_for_status()
        
        return response.json()
    
    def finalize_app_bundle(self, app_bundle_id):
        """Finalize an app bundle to start processing"""
        url = f'{self.base_url}/app-bundles/{app_bundle_id}/finalize'

        response = self.client.post(url, json={}, headers=self.headers)
        response.raise_for_status()

        return response.json()

    def create_app_bundle_from_existing(self, app_id, build_id, bundle_name, files=None):
        """Create an app bundle from existing build and files

        Args:
            app_id: ID of the app
            build_id: ID of existing app build/version
            bundle_name: Name for the bundle
            files: Optional list of dicts with 'fileId' and optional 'path'

        Returns:
            Bundle creation response with bundle ID
        """
        url = f'{self.base_url}/app-bundles'

        data = {
            'appId': app_id,
            'appBuildId': build_id,
            'appBundleName': bundle_name
        }

        if files:
            data['files'] = files

        response = self.client.post(url, json=data, headers=self.headers)
        response.raise_for_status()

        return response.json()

    def upload_app_bundle(self, app_id, folder_path, bundle_name, version_number, release_notes, silent):
        """Upload APK/ZIP and all bundle files from folder with hash-based deduplication, then finalize bundle"""
        from abxr.apps import AppsService
        from abxr.files import FilesService

        # Find single APK or ZIP file in folder root
        folder = Path(folder_path)
        if not folder.is_dir():
            raise ValueError(f"Folder path does not exist: {folder_path}")

        apk_files = list(folder.glob('*.apk'))
        zip_files = list(folder.glob('*.zip'))
        build_files = apk_files + zip_files

        if len(build_files) == 0:
            raise ValueError(f"No APK or ZIP file found in folder: {folder_path}")
        elif len(build_files) > 1:
            raise ValueError(f"Multiple APK/ZIP files found in folder. Expected exactly one. Found: {[f.name for f in build_files]}")

        build_file = build_files[0]

        if not silent:
            print(f"Found build file: {build_file.name}")

        # Calculate build hash
        if not silent:
            print(f"Calculating build hash...")
        build_hash = self.calculate_sha256(str(build_file))

        # Find all bundle files (excluding system files)
        all_files = [f for f in folder.rglob('*')
                     if f.is_file()
                     and f != build_file
                     and f.name not in ['.DS_Store', 'Thumbs.db']]

        # Calculate file hashes
        file_hashes = {}
        if all_files and not silent:
            print(f"Calculating hashes for {len(all_files)} bundle file(s)...")
        for file_path in all_files:
            file_hashes[file_path] = self.calculate_sha512(str(file_path))

        # Query for existing resources
        apps_service = AppsService(self.base_url, self.headers['Authorization'].replace('Bearer ', ''))

        if not silent:
            print(f"Checking for existing build...")
        existing_builds = apps_service.get_versions_by_sha256(app_id, [build_hash])
        existing_build = existing_builds[0] if existing_builds else None

        # Query for existing files (batch up to 10 at a time)
        existing_files_map = {}
        if file_hashes:
            if not silent:
                print(f"Checking for existing files...")
            hash_list = list(file_hashes.values())
            for i in range(0, len(hash_list), 10):
                batch_hashes = hash_list[i:i + 10]
                existing_files_batch = apps_service.get_files_by_sha512(app_id, batch_hashes)
                for file_data in existing_files_batch:
                    file_hash = file_data.get('sha512')
                    file_name = file_data.get('name')
                    # Match by hash AND filename for safety
                    for file_path, path_hash in file_hashes.items():
                        if path_hash == file_hash and file_path.name == file_name:
                            existing_files_map[file_path] = file_data

        # Branch based on whether build exists
        if existing_build:
            if not silent:
                print(f"Build found (reusing existing version {existing_build.get('id')})")

            # Create bundle from existing build
            build_id = existing_build['id']

            # Prepare files array for bundle creation
            bundle_files = []
            for file_path, file_data in existing_files_map.items():
                rel_path = file_path.relative_to(folder)
                rel_dir = rel_path.parent
                if str(rel_dir) == '.':
                    device_path = "/sdcard"
                else:
                    device_path = f"/sdcard/{str(rel_dir).replace(os.sep, '/')}"

                bundle_files.append({
                    'fileId': file_data['id'],
                    'path': device_path
                })

            if not silent:
                print(f"Creating bundle with existing build...")
            bundle_response = self.create_app_bundle_from_existing(
                app_id,
                build_id,
                bundle_name,
                bundle_files if bundle_files else None
            )

            app_bundle_id = bundle_response.get('id')
            if not app_bundle_id:
                raise ValueError("No bundle ID returned from bundle creation.")

            if not silent:
                print(f"Bundle created with ID: {app_bundle_id}")

            # Upload missing files
            files_to_upload = [f for f in all_files if f not in existing_files_map]
            if files_to_upload:
                if not silent:
                    print(f"Uploading {len(files_to_upload)} new file(s)...")
                files_service = FilesService(self.base_url, self.headers['Authorization'].replace('Bearer ', ''))

                for file_path in files_to_upload:
                    rel_path = file_path.relative_to(folder)
                    rel_dir = rel_path.parent
                    if str(rel_dir) == '.':
                        device_path = "/sdcard"
                    else:
                        device_path = f"/sdcard/{str(rel_dir).replace(os.sep, '/')}"

                    if not silent:
                        print(f"Uploading {rel_path} -> {device_path}/{file_path.name}")

                    files_service.upload_file(
                        str(file_path),
                        device_path,
                        silent,
                        app_bundle_id=app_bundle_id
                    )

            if existing_files_map and not silent:
                print(f"Reused {len(existing_files_map)} existing file(s)")

        else:
            # Build doesn't exist - upload it
            if not silent:
                print(f"Existing build not found, uploading new build and creating bundle '{bundle_name}'...")

            upload_response = apps_service.upload_file(
                app_id,
                str(build_file),
                version_number,
                release_notes,
                silent,
                wait=False,
                app_bundle_name=bundle_name
            )

            app_bundle_id = upload_response.get('appBundleId')
            if not app_bundle_id:
                raise ValueError("No appBundleId returned from upload. Bundle may not have been created.")

            if not silent:
                print(f"Bundle created with ID: {app_bundle_id}")

            # Add existing files to bundle
            if existing_files_map:
                if not silent:
                    file_names = [file_path.name for file_path in existing_files_map.keys()]
                    total_count = len(file_names)

                    if total_count <= 10:
                        files_list = ", ".join(file_names)
                        print(f"Adding {total_count} existing file(s) to bundle: {files_list}")
                    else:
                        first_10 = ", ".join(file_names[:10])
                        remaining = total_count - 10
                        print(f"Adding {total_count} existing file(s) to bundle: {first_10} +{remaining} other files")

                files_to_add = []
                for file_path, file_data in existing_files_map.items():
                    rel_path = file_path.relative_to(folder)
                    rel_dir = rel_path.parent
                    if str(rel_dir) == '.':
                        device_path = "/sdcard"
                    else:
                        device_path = f"/sdcard/{str(rel_dir).replace(os.sep, '/')}"

                    files_to_add.append({
                        'fileId': file_data['id'],
                        'path': device_path
                    })

                self.add_files_to_app_bundle(app_bundle_id, files_to_add)

            # Upload missing files
            files_to_upload = [f for f in all_files if f not in existing_files_map]
            if files_to_upload:
                if not silent:
                    print(f"Uploading {len(files_to_upload)} new file(s)...")
                files_service = FilesService(self.base_url, self.headers['Authorization'].replace('Bearer ', ''))

                for file_path in files_to_upload:
                    rel_path = file_path.relative_to(folder)
                    rel_dir = rel_path.parent
                    if str(rel_dir) == '.':
                        device_path = "/sdcard"
                    else:
                        device_path = f"/sdcard/{str(rel_dir).replace(os.sep, '/')}"

                    if not silent:
                        print(f"Uploading {rel_path} -> {device_path}/{file_path.name}")

                    files_service.upload_file(
                        str(file_path),
                        device_path,
                        silent,
                        app_bundle_id=app_bundle_id
                    )

            if existing_files_map and not silent:
                print(f"Reused {len(existing_files_map)} existing file(s)")

        # Finalize the bundle
        if not silent:
            print(f"Finalizing bundle...")

        finalize_response = self.finalize_app_bundle(app_bundle_id)

        if not silent:
            print(f"Bundle finalized successfully. Bundle is processing and will be available once all build and files are processed and available.")
            print(f"Check bundle status: abxr-cli app_bundles details {app_bundle_id}")

        return finalize_response


class CommandHandler:
    def __init__(self, args):
        self.args = args
        self.service = AppBundlesService(self.args.url, self.args.token)

    def run(self):
        if self.args.app_bundles_command == Commands.UPLOAD.value:
            result = self.service.upload_app_bundle(
                self.args.app_id,
                self.args.folder_path,
                self.args.bundle_name,
                self.args.version_number,
                self.args.notes,
                self.args.silent
            )
            print_formatted(self.args.format, result)

        elif self.args.app_bundles_command == Commands.FINALIZE.value:
            result = self.service.finalize_app_bundle(self.args.app_bundle_id)
            print_formatted(self.args.format, result)

        elif self.args.app_bundles_command == Commands.DETAILS.value:
            app_bundle_detail = self.service.get_app_bundle_detail(self.args.app_bundle_id)
            print_formatted(self.args.format, app_bundle_detail)

        elif self.args.app_bundles_command == Commands.LIST.value:
            app_bundles = self.service.get_all_app_bundles_for_app(self.args.app_id, self.args.status)
            print_formatted(self.args.format, app_bundles)

        elif self.args.app_bundles_command == Commands.ADD_FILES.value:
            files = []
            for file_item in self.args.files:
                file_parts = file_item.split(':')
                file_dict = {'fileId': file_parts[0]}
                if len(file_parts) > 1:
                    file_dict['path'] = file_parts[1]
                files.append(file_dict)

            result = self.service.add_files_to_app_bundle(self.args.app_bundle_id, files)
            print_formatted(self.args.format, result)
