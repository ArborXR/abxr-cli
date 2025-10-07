#!/usr/bin/env python3
#
# Copyright (c) 2024-2025 ABXR Labs, Inc.
# Released under the MIT License. See LICENSE file for details.
#

import os
from tqdm import tqdm
import time
import hashlib
from pathlib import Path

from enum import Enum

from abxr.api_service import ApiService
from abxr.multipart import MultipartFileS3
from abxr.formats import DataOutputFormats
from abxr.output import print_formatted

class Commands(Enum):
    LIST = "list"             # List app bundles for an app
    DETAILS = "details"       # Get details of a specific app bundle
    CREATE = "create"         # Create a new app bundle
    ADD_FILES = "add_files"   # Add files to an app bundle
    UPLOAD = "upload"         # Upload a new bundle version

class AppBundlesService(ApiService):
    def __init__(self, base_url, token):
        super().__init__(base_url, token)

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
    
    def create_app_bundle(self, app_build_id, name, files=None):
        """Create a new app bundle from an existing app version"""
        url = f'{self.base_url}/app-bundles'
        
        data = {
            'appBuildId': app_build_id,
            'appBundleName': name
        }

        if files:

        
        response = self.client.post(url, json=data, headers=self.headers)
        response.raise_for_status()
        
        return response.json()
    
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
    
    def calculate_file_hash(self, file_path):
        """Calculate SHA-256 hash of a file"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            # Read and update hash in chunks of 4K
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def upload_file(self, file_path, silent=False):
        """Upload a file and return its ID"""
        # This is a simplified version, you'll need to implement the actual file upload logic
        # similar to how it's done in the files.py module
        url = f'{self.base_url}/files'
        
        with open(file_path, 'rb') as file:
            files = {'file': (os.path.basename(file_path), file)}
            with tqdm(total=os.path.getsize(file_path), unit='B', unit_scale=True, 
                     desc=f'Uploading {os.path.basename(file_path)}', disable=silent) as pbar:
                
                # Custom adapter to update progress bar
                def upload_callback(monitor):
                    pbar.update(monitor.bytes_read - pbar.n)
                
                # Use requests-toolbelt for upload progress if available
                try:
                    from requests_toolbelt import MultipartEncoder, MultipartEncoderMonitor
                    encoder = MultipartEncoder(fields=files)
                    monitor = MultipartEncoderMonitor(encoder, upload_callback)
                    headers = self.headers.copy()
                    headers['Content-Type'] = monitor.content_type
                    response = self.client.post(url, data=monitor, headers=headers)
                except ImportError:
                    # Fall back to regular upload without progress
                    response = self.client.post(url, files=files, headers=self.headers)
        
        response.raise_for_status()
        return response.json()
    
    def add_directory_to_app_bundle(self, app_bundle_id, directory_path, target_path="", silent=False):
        """Add all files from a directory to an app bundle
        
        Args:
            app_bundle_id: ID of the app bundle
            directory_path: Local path to the directory containing files
            target_path: Base path in the bundle where files should be placed
            silent: Whether to suppress progress output
        """
        # Step 1: Get existing files in the bundle to compare hashes
        existing_files = self.get_all_files_for_app_bundle(app_bundle_id)
        existing_file_map = {}
        
        # Create a map of path -> {id, hash} for quick lookup
        for file in existing_files:
            if 'path' in file and 'hash' in file:
                existing_file_map[file['path']] = {
                    'id': file['id'],
                    'hash': file['hash']
                }
        
        # Step 2: Scan the directory and process files
        directory_path = Path(directory_path)
        files_to_add = []
        files_processed = 0
        files_skipped = 0
        files_added = 0
        
        # Get all files recursively
        all_files = [f for f in directory_path.glob('**/*') if f.is_file()]
        
        for file_path in tqdm(all_files, desc="Processing files", disable=silent):
            files_processed += 1
            
            # Calculate relative path for the bundle
            rel_path = file_path.relative_to(directory_path)
            if target_path:
                bundle_path = os.path.join(target_path, str(rel_path)).replace('\\', '/')
            else:
                bundle_path = str(rel_path).replace('\\', '/')
                
            # Calculate file hash
            file_hash = self.calculate_file_hash(file_path)
            
            # Check if file exists with same hash
            if bundle_path in existing_file_map and existing_file_map[bundle_path]['hash'] == file_hash:
                if not silent:
                    print(f"Skipping {bundle_path} (unchanged)")
                files_skipped += 1
                continue
            
            # File is new or changed, upload it
            if not silent:
                print(f"Uploading {bundle_path}")
                
            # Upload the file
            uploaded_file = self.upload_file(file_path, silent)
            file_id = uploaded_file['id']
            
            # Add to list of files to include in bundle
            files_to_add.append({
                'fileId': file_id,
                'path': bundle_path
            })
            files_added += 1
        
        # Step 3: Add the files to the bundle
        result = None
        if files_to_add:
            result = self.add_files_to_app_bundle(app_bundle_id, files_to_add)
        
        # Return summary
        return {
            'filesProcessed': files_processed,
            'filesAdded': files_added,
            'filesSkipped': files_skipped,
            'result': result
        }
    
    def upload_app_bundle(self, app_id, name, path):
        #
        #
        #
        pass


class CommandHandler:
    def __init__(self, args):
        self.args = args
        self.service = AppBundlesService(self.args.url, self.args.token)

    def run(self):
        if self.args.app_bundles_command == Commands.LIST.value:            
            app_bundles = self.service.get_all_app_bundles_for_app(self.args.app_id, self.args.status)
            print_formatted(self.args.format, app_bundles)
            
        elif self.args.app_bundles_command == Commands.DETAILS.value:
            app_bundle_detail = self.service.get_app_bundle_detail(self.args.app_bundle_id)
            print_formatted(self.args.format, app_bundle_detail)

        elif self.args.app_bundles_command == Commands.FILE_LIST.value:
            if hasattr(self.args, 'app_bundle_id'):
                # Get files for a specific app bundle
                files = self.service.get_all_files_for_app_bundle(self.args.app_bundle_id)
            else:
                # Get all bundled files for an app
                files = self.service.get_all_bundled_files_for_app(self.args.app_id)
            print_formatted(self.args.format, files)
        
        elif self.args.app_bundles_command == Commands.CREATE.value:
            app_bundle = self.service.create_app_bundle(
                self.args.app_build_id,
                self.args.name,
                self.args.files
            )
            print_formatted(self.args.format, app_bundle)
            
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
            
        elif self.args.app_bundles_command == Commands.UPLOAD.value:
            app_bundle = self.service.upload_app_bundle(
                self.args.app_id,
                self.args.name,
                self.args.path
            )
            print_formatted(self.args.format, app_bundle)
