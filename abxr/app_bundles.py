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
from abxr.constants import SYSTEM_FILES_TO_EXCLUDE, SYSTEM_DIRS_TO_EXCLUDE
from abxr.multipart import MultipartFileS3
from abxr.formats import DataOutputFormats
from abxr.output import print_formatted
from abxr.apps import AppsService
from abxr.files import FilesService

class Commands(Enum):
    LIST = "list"             # List app bundles for an app
    DETAILS = "details"       # Get details of a specific app bundle
    UPLOAD = "upload"         # Upload a new bundle version
    ADD_FILES = "add_files"   # Add files to an app bundle
    FINALIZE = "finalize"     # Finalize an app bundle
    RESUME = "resume"         # Resume a failed bundle upload
    UPDATE_LABEL = "update_label"  # Update a bundle's label
    CREATE_FROM_BUILD = "create_from_build"  # Create bundle from existing build

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
        """Finalize an app bundle to start processing

        Returns:
            AppBundle object with id, status, label, appBuild, createdAt, updatedAt
        """
        url = f'{self.base_url}/app-bundles/{app_bundle_id}/finalize'

        response = self.client.post(url, json={}, headers=self.headers)
        response.raise_for_status()

        return response.json()

    def update_app_bundle_label(self, app_bundle_id, label):
        """Update an app bundle's label

        Args:
            app_bundle_id: ID of the app bundle to update
            label: New label string (max 60 chars) or None to remove the label

        Returns:
            AppBundle object with updated label
        """
        url = f'{self.base_url}/app-bundles/{app_bundle_id}'

        data = {'label': label}

        response = self.client.patch(url, json=data, headers=self.headers)
        response.raise_for_status()

        return response.json()

    def _validate_bundle_files_match(self, bundle_files, local_file_hashes, folder, base_path=None):
        """Validate that existing bundle files match local folder structure

        Args:
            bundle_files: List of file dicts from API with 'name', 'location', 'sha512'
            local_file_hashes: Dict of {Path: sha512_hash} for local files
            folder: Path object for the local folder root
            base_path: Optional base path on device relative to /sdcard

        Raises:
            ValueError: If any bundle file doesn't match local structure
        """
        mismatches = []

        for bundle_file in bundle_files:
            file_name = bundle_file.get('name')
            bundle_location = bundle_file.get('location')
            bundle_hash = bundle_file.get('sha512')

            # Find local file with matching name
            local_file = None
            for path in local_file_hashes.keys():
                if path.name == file_name:
                    local_file = path
                    break

            if not local_file:
                mismatches.append(f"  - {file_name}: not found locally")
                continue

            # Check hash
            local_hash = local_file_hashes[local_file]
            if local_hash != bundle_hash:
                mismatches.append(f"  - {file_name}: content changed (hash mismatch)")
                continue

            # Check path
            computed_path = self._compute_device_path(local_file, folder, base_path)

            if computed_path != bundle_location:
                mismatches.append(f"  - {file_name}: path changed (bundle: {bundle_location}, local: {computed_path})")
                continue

        if mismatches:
            error_msg = "Cannot resume bundle - folder structure has changed:\n"
            error_msg += "\n".join(mismatches)
            error_msg += "\n\nTo resume, restore the original folder structure."
            error_msg += "\nTo create a new bundle with these changes, use the upload command."
            raise ValueError(error_msg)

    def _compute_device_path(self, file_path, folder, base_path=None):
        """Compute /sdcard device path for a file relative to folder root

        Args:
            file_path: Path object for the file
            folder: Path object for the folder root
            base_path: Optional base path relative to /sdcard (e.g., "myapp/config")

        Returns:
            Device path string (e.g., "/sdcard" or "/sdcard/data/cache" or "/sdcard/myapp/config/data")
        """
        rel_path = file_path.relative_to(folder)
        rel_dir = rel_path.parent

        # Build path components
        if base_path:
            # Start with /sdcard/{base_path}
            if str(rel_dir) == '.':
                return f"/sdcard/{base_path}"
            else:
                return f"/sdcard/{base_path}/{str(rel_dir).replace(os.sep, '/')}"
        else:
            # Original behavior: /sdcard or /sdcard/{rel_dir}
            if str(rel_dir) == '.':
                return "/sdcard"
            else:
                return f"/sdcard/{str(rel_dir).replace(os.sep, '/')}"

    def _prepare_existing_files_for_bundle(self, existing_files_map, folder, base_path=None):
        """Prepare existing files array for bundle creation/addition

        Args:
            existing_files_map: Dict of {Path: file_data} for existing files
            folder: Path object for the folder root
            base_path: Optional base path on device relative to /sdcard

        Returns:
            List of dicts with 'fileId' and 'path' for API
        """
        files_to_add = []
        for file_path, file_data in existing_files_map.items():
            device_path = self._compute_device_path(file_path, folder, base_path)
            files_to_add.append({
                'fileId': file_data['id'],
                'path': device_path
            })
        return files_to_add

    def _finalize_and_return_bundle_info(self, bundle_id, silent):
        """Finalize bundle and return bundle info from API

        Args:
            bundle_id: ID of the bundle to finalize
            silent: Suppress output

        Returns:
            AppBundle object from API with full details
        """
        if not silent:
            print(f"Finalizing bundle...")

        bundle_response = self.finalize_app_bundle(bundle_id)

        if not silent:
            print(f"Bundle finalized successfully. Bundle is processing and will be available once all build and files are processed and available.")
            print(f"Check bundle status: abxr-cli app_bundles details {bundle_id}")

        return bundle_response

    def _query_existing_files_by_hash(self, app_id, file_hashes, silent):
        """Query for existing files by SHA512 hash with hash-based deduplication

        Args:
            app_id: ID of the app
            file_hashes: Dict of {Path: sha512_hash} for files to check
            silent: Suppress output

        Returns:
            Dict of {Path: file_data} for files that already exist in the app
        """
        existing_files_map = {}
        if not file_hashes:
            return existing_files_map

        apps_service = AppsService(self.base_url, self.headers['Authorization'].replace('Bearer ', ''))

        if not silent:
            print(f"Checking for existing files...")

        # Query in batches of 10
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

        return existing_files_map

    def _upload_bundle_files(self, files_to_upload, folder, app_bundle_id, silent, base_path=None):
        """Upload bundle files to an app bundle

        Args:
            files_to_upload: List of Path objects to upload
            folder: Path object for the folder root
            app_bundle_id: ID of the bundle to upload files to
            silent: Suppress output
            base_path: Optional base path on device relative to /sdcard
        """
        if not files_to_upload:
            return

        if not silent:
            print(f"Uploading {len(files_to_upload)} new file(s)...")

        files_service = FilesService(self.base_url, self.headers['Authorization'].replace('Bearer ', ''))

        for file_path in files_to_upload:
            rel_path = file_path.relative_to(folder)
            device_path = self._compute_device_path(file_path, folder, base_path)

            if not silent:
                print(f"Uploading {rel_path} -> {device_path}/{file_path.name}")

            files_service.upload_file(
                str(file_path),
                device_path,
                silent,
                app_bundle_id=app_bundle_id
            )

    def _scan_folder(self, folder_path, apk_path, silent=False):
        """Scan folder for bundle files and validate APK, calculate hashes

        Args:
            folder_path: Path to folder containing bundle files
            apk_path: Path to APK file
            silent: Suppress output

        Returns:
            tuple: (folder, build_file, build_hash, file_hashes_dict)
                - folder: Path object
                - build_file: Path to APK file
                - build_hash: SHA-256 hash of build
                - file_hashes_dict: {Path: sha512_hash} for all bundle files
        """
        # Validate APK path
        build_file = Path(apk_path)
        if not build_file.exists() or not build_file.is_file():
            raise ValueError(f"APK file not found: {apk_path}")

        # Validate file extension - .zip not supported for bundles
        if build_file.suffix.lower() == '.zip':
            raise ValueError(
                f"ZIP files are not supported for app bundle uploads.\n"
                f"Please unpack '{build_file.name}' to a folder and use the extracted folder as the bundle_folder parameter.\n"
                f"The APK file should be specified separately with the apk_path parameter."
            )

        if not silent:
            print(f"Using build file: {build_file.name}")

        # Calculate build hash
        if not silent:
            print(f"Calculating build hash...")
        build_hash = self.calculate_sha256(str(build_file))

        # Scan folder for bundle files (reuse common logic, exclude the APK)
        folder, file_hashes = self._scan_folder_files_only(folder_path, silent, exclude_file=build_file)

        return folder, build_file, build_hash, file_hashes

    def _scan_folder_files_only(self, folder_path, silent=False, exclude_file=None):
        """Scan folder for bundle files only (no APK required), calculate hashes

        Args:
            folder_path: Path to folder containing bundle files
            silent: Suppress output
            exclude_file: Optional file path to exclude (e.g., APK file)

        Returns:
            tuple: (folder, file_hashes_dict)
                - folder: Path object
                - file_hashes_dict: {Path: sha512_hash} for all bundle files
        """
        # Validate folder
        folder = Path(folder_path)
        if not folder.is_dir():
            raise ValueError(f"Folder path does not exist: {folder_path}")

        # Convert exclude_file to Path if provided
        exclude_path = Path(exclude_file) if exclude_file else None

        # Find all bundle files (excluding system files and optional exclude_file)
        all_files = [f for f in folder.rglob('*')
                     if f.is_file()
                     and f.name not in SYSTEM_FILES_TO_EXCLUDE
                     and not any(sys_dir in str(f) for sys_dir in SYSTEM_DIRS_TO_EXCLUDE)
                     and (exclude_path is None or f != exclude_path)]

        # Calculate file hashes
        file_hashes = {}
        if all_files and not silent:
            print(f"Calculating hashes for {len(all_files)} bundle file(s)...")
        for file_path in all_files:
            file_hashes[file_path] = self.calculate_sha512(str(file_path))

        return folder, file_hashes

    def create_app_bundle_from_existing(self, build_id, files=None, release_channel_id=None, new_release_channel_title=None):
        """Create an app bundle from existing build and files

        Args:
            build_id: ID of existing app build/version
            files: Optional list of dicts with 'fileId' and optional 'path'
            release_channel_id: Optional ID of existing release channel
            new_release_channel_title: Optional title for new release channel

        Returns:
            Bundle creation response with bundle ID
        """
        url = f'{self.base_url}/app-bundles'

        data = {
            'appBuildId': build_id
        }

        if files:
            data['files'] = files

        if release_channel_id:
            data['releaseChannelId'] = release_channel_id

        if new_release_channel_title:
            data['newReleaseChannelTitle'] = new_release_channel_title

        response = self.client.post(url, json=data, headers=self.headers)
        response.raise_for_status()

        return response.json()

    def upload_app_bundle(self, app_id, folder_path, version_number, release_notes, silent, apk_path, device_path=None, release_channel_id=None, new_release_channel_title=None):
        """Upload APK and all bundle files from folder with hash-based deduplication, then finalize bundle

        Args:
            app_id: ID of the app
            folder_path: Path to folder containing bundle files
            version_number: Optional version number for the build
            release_notes: Optional release notes
            silent: Suppress output
            apk_path: Path to APK file
            device_path: Optional base path on device relative to /sdcard
            release_channel_id: Optional ID of existing release channel to upload to
            new_release_channel_title: Optional title for a new release channel to create
        """
        # Scan folder for build and files
        folder, build_file, build_hash, file_hashes = self._scan_folder(folder_path, apk_path, silent)
        all_files = list(file_hashes.keys())

        # Query for existing resources
        apps_service = AppsService(self.base_url, self.headers['Authorization'].replace('Bearer ', ''))

        if not silent:
            print(f"Checking for existing build...")
        existing_builds = apps_service.get_versions_by_sha256(app_id, [build_hash])
        existing_build = existing_builds[0] if existing_builds else None

        # Query for existing files
        existing_files_map = self._query_existing_files_by_hash(app_id, file_hashes, silent)

        # Branch based on whether build exists
        if existing_build:
            if not silent:
                print(f"Build found (reusing existing version {existing_build.get('id')})")

            # Create bundle from existing build
            build_id = existing_build['id']

            # Prepare files array for bundle creation
            bundle_files = self._prepare_existing_files_for_bundle(existing_files_map, folder, device_path)

            if not silent:
                print(f"Creating bundle with existing build...")
            bundle_response = self.create_app_bundle_from_existing(
                build_id,
                bundle_files if bundle_files else None,
                release_channel_id=release_channel_id,
                new_release_channel_title=new_release_channel_title
            )

            app_bundle_id = bundle_response.get('id')
            if not app_bundle_id:
                raise ValueError("No bundle ID returned from bundle creation.")

            if not silent:
                print(f"Bundle created with ID: {app_bundle_id}")

            try:
                # Upload missing files
                files_to_upload = [f for f in all_files if f not in existing_files_map]
                self._upload_bundle_files(files_to_upload, folder, app_bundle_id, silent, device_path)

                if existing_files_map and not silent:
                    print(f"Reused {len(existing_files_map)} existing file(s)")
            except Exception as e:
                print(f"\nError during bundle upload: {e}")
                print(f"\nBundle ID: {app_bundle_id}")
                print(f"The bundle is in 'pending' state and can be resumed using:")
                device_path_arg = f" --device-path {device_path}" if device_path else ""
                print(f"  abxr-cli app_bundles resume {app_bundle_id} {str(build_file)} {folder_path}{device_path_arg}")
                raise

        else:
            # Build doesn't exist - upload it
            if not silent:
                print(f"Existing build not found, uploading new build and creating bundle...")

            upload_response = apps_service.upload_file(
                app_id,
                str(build_file),
                version_number,
                release_notes,
                silent,
                wait=False,
                app_build_type="app-bundle",
                release_channel_id=release_channel_id,
                new_release_channel_title=new_release_channel_title
            )

            app_bundle_id = upload_response.get('appBundleId')
            if not app_bundle_id:
                raise ValueError("No appBundleId returned from upload. Bundle may not have been created.")

            if not silent:
                print(f"Bundle created with ID: {app_bundle_id}")

            try:
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

                    files_to_add = self._prepare_existing_files_for_bundle(existing_files_map, folder, device_path)
                    self.add_files_to_app_bundle(app_bundle_id, files_to_add)

                # Upload missing files
                files_to_upload = [f for f in all_files if f not in existing_files_map]
                self._upload_bundle_files(files_to_upload, folder, app_bundle_id, silent, device_path)

                if existing_files_map and not silent:
                    print(f"Reused {len(existing_files_map)} existing file(s)")
            except Exception as e:
                print(f"\nError during bundle upload: {e}")
                print(f"\nBundle ID: {app_bundle_id}")
                print(f"The bundle is in 'pending' state and can be resumed using:")
                device_path_arg = f" --device-path {device_path}" if device_path else ""
                print(f"  abxr-cli app_bundles resume {app_bundle_id} {str(build_file)} {folder_path}{device_path_arg}")
                raise

        # Finalize and return bundle info
        return self._finalize_and_return_bundle_info(app_bundle_id, silent)

    def resume_app_bundle(self, bundle_id, apk_path, folder_path, silent, device_path=None):
        """Resume a failed or interrupted bundle upload

        Args:
            bundle_id: ID of the existing bundle to resume
            apk_path: Path to APK file
            folder_path: Path to folder containing bundle files
            silent: Suppress output
            device_path: Optional base path on device relative to /sdcard (must match original upload)

        Raises:
            ValueError: If bundle cannot be resumed (wrong status, file mismatch, etc.)
        """
        # Get bundle details
        if not silent:
            print(f"Fetching bundle details...")
        bundle = self.get_app_bundle_detail(bundle_id)

        # Validate bundle status
        bundle_status = bundle.get('status')
        if bundle_status != 'pending':
            raise ValueError(f"Cannot resume bundle - status is '{bundle_status}'. Only 'pending' bundles can be resumed.")

        # Scan local folder with provided APK path
        folder, build_file, build_hash, file_hashes = self._scan_folder(folder_path, apk_path, silent)

        # Validate build matches
        bundle_build = bundle.get('appBuild', {})
        bundle_build_hash = bundle_build.get('sha256')

        if not bundle_build_hash:
            raise ValueError("Bundle does not have an associated build")

        if build_hash != bundle_build_hash:
            raise ValueError(
                f"Cannot resume bundle - build file mismatch.\n"
                f"Bundle was created with a different build file.\n"
                f"Expected SHA-256: {bundle_build_hash[:16]}...\n"
                f"Found SHA-256:    {build_hash[:16]}..."
            )

        if not silent:
            print(f"Build verified (matches bundle build)")

        # Get existing bundle files
        if not silent:
            print(f"Fetching bundle files...")
        bundle_files = self.get_all_files_for_app_bundle(bundle_id)

        # Validate existing bundle files match local structure
        if bundle_files:
            if not silent:
                print(f"Validating {len(bundle_files)} existing file(s)...")
            self._validate_bundle_files_match(bundle_files, file_hashes, folder, device_path)
            if not silent:
                print(f"All existing files verified")

        # Determine missing files
        bundle_file_hashes = {f.get('sha512') for f in bundle_files if f.get('sha512')}
        files_to_upload = [path for path, hash in file_hashes.items()
                          if hash not in bundle_file_hashes]

        if not files_to_upload:
            if not silent:
                print(f"All files already uploaded to bundle")
        else:
            self._upload_bundle_files(files_to_upload, folder, bundle_id, silent, device_path)

        # Finalize and return bundle info
        return self._finalize_and_return_bundle_info(bundle_id, silent)

    def create_app_bundle_from_build(self, build_id, folder_path, app_id, silent, device_path=None, release_channel_id=None, new_release_channel_title=None):
        """Create an app bundle from an existing build ID and folder of files

        Args:
            build_id: ID of existing app build/version
            folder_path: Path to folder containing bundle files
            app_id: ID of the app (needed for file deduplication queries)
            silent: Suppress output
            device_path: Optional base path on device relative to /sdcard
            release_channel_id: Optional ID of existing release channel
            new_release_channel_title: Optional title for new release channel

        Returns:
            AppBundle object with full details after finalization
        """
        # Scan folder for files only (no APK needed)
        folder, file_hashes = self._scan_folder_files_only(folder_path, silent)
        all_files = list(file_hashes.keys())

        # Query for existing files
        existing_files_map = self._query_existing_files_by_hash(app_id, file_hashes, silent)

        # Prepare files array for bundle creation
        bundle_files = self._prepare_existing_files_for_bundle(existing_files_map, folder, device_path)

        if not silent:
            print(f"Creating bundle from existing build ID {build_id}...")

        bundle_response = self.create_app_bundle_from_existing(
            build_id,
            bundle_files if bundle_files else None,
            release_channel_id=release_channel_id,
            new_release_channel_title=new_release_channel_title
        )

        app_bundle_id = bundle_response.get('id')
        if not app_bundle_id:
            raise ValueError("No bundle ID returned from bundle creation.")

        if not silent:
            print(f"Bundle created with ID: {app_bundle_id}")

        try:
            # Add existing files that were matched
            if existing_files_map and not silent:
                file_names = [file_path.name for file_path in existing_files_map.keys()]
                total_count = len(file_names)

                if total_count <= 10:
                    files_list = ", ".join(file_names)
                    print(f"Reusing {total_count} existing file(s): {files_list}")
                else:
                    first_10 = ", ".join(file_names[:10])
                    remaining = total_count - 10
                    print(f"Reusing {total_count} existing file(s): {first_10} +{remaining} other files")

            # Upload missing files
            files_to_upload = [f for f in all_files if f not in existing_files_map]
            self._upload_bundle_files(files_to_upload, folder, app_bundle_id, silent, device_path)

        except Exception as e:
            print(f"\nError during bundle creation: {e}")
            print(f"\nBundle ID: {app_bundle_id}")
            print(f"The bundle is in 'pending' state and can be finalized using:")
            print(f"  abxr-cli app_bundles finalize {app_bundle_id}")
            raise

        # Finalize and return bundle info
        return self._finalize_and_return_bundle_info(app_bundle_id, silent)


class CommandHandler:
    def __init__(self, args):
        self.args = args
        self.service = AppBundlesService(self.args.url, self.args.token)

    def run(self):
        if self.args.app_bundles_command == Commands.UPLOAD.value:
            result = self.service.upload_app_bundle(
                self.args.app_id,
                self.args.bundle_folder,
                getattr(self.args, 'version_number', None),
                self.args.notes,
                self.args.silent,
                apk_path=self.args.apk_path,
                device_path=getattr(self.args, 'device_path', None),
                release_channel_id=getattr(self.args, 'release_channel_id', None),
                new_release_channel_title=getattr(self.args, 'new_release_channel_title', None)
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

        elif self.args.app_bundles_command == Commands.RESUME.value:
            result = self.service.resume_app_bundle(
                self.args.bundle_id,
                self.args.apk_path,
                self.args.folder_path,
                self.args.silent,
                device_path=getattr(self.args, 'device_path', None)
            )
            print_formatted(self.args.format, result)

        elif self.args.app_bundles_command == Commands.UPDATE_LABEL.value:
            # Determine label value: None if --clear flag is used, otherwise use --label value
            label = None if self.args.clear else self.args.label
            result = self.service.update_app_bundle_label(self.args.app_bundle_id, label)
            print_formatted(self.args.format, result)

        elif self.args.app_bundles_command == Commands.CREATE_FROM_BUILD.value:
            result = self.service.create_app_bundle_from_build(
                self.args.build_id,
                self.args.bundle_folder,
                self.args.app_id,
                self.args.silent,
                device_path=getattr(self.args, 'device_path', None),
                release_channel_id=getattr(self.args, 'release_channel_id', None),
                new_release_channel_title=getattr(self.args, 'new_release_channel_title', None)
            )
            print_formatted(self.args.format, result)
