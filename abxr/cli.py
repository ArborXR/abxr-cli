#!/usr/bin/env python3
#
# Copyright (c) 2024-2025 ABXR Labs, Inc.
# Released under the MIT License. See LICENSE file for details.
#

import argparse
import os

from abxr.version import version
from abxr.formats import DataOutputFormats

from abxr.apps import Commands as AppCommands, CommandHandler as AppsCommandHandler
from abxr.files import Commands as FileCommands, CommandHandler as FilesCommandHandler

ABXR_API_URL = os.environ.get("ABXR_API_URL", "https://api.xrdm.app/api/v2")
ABXR_API_TOKEN = os.environ.get("ABXR_API_TOKEN")

def main():
    parser = argparse.ArgumentParser(description=f'%(prog)s {version}')
    parser.add_argument("-u", "--url", help="API Base URL", type=str, default=ABXR_API_URL)
    parser.add_argument("-t", "--token", help="API Token", type=str, default=ABXR_API_TOKEN)
    parser.add_argument("-f", "--format", help="Data Output format", type=str, choices=[DataOutputFormats.JSON.value, DataOutputFormats.YAML.value], default=DataOutputFormats.YAML.value)
    parser.add_argument('-v', '--version', action='version', version=f'%(prog)s {version}')

    subparsers = parser.add_subparsers(dest="command", help="Sub-command help")

    apps_parser = subparsers.add_parser("apps", help="Apps command")
    apps_subparsers = apps_parser.add_subparsers(dest="apps_command", help="Apps command help")

    # List All Apps
    apps_list_parser = apps_subparsers.add_parser(AppCommands.LIST.value, help="List apps")

    # Detail of App
    app_detail_parser = apps_subparsers.add_parser(AppCommands.DETAILS.value, help="Detail of an app")
    app_detail_parser.add_argument("app_id", help="ID of the app", type=str)

    # List Release Channels
    release_channels_list_parser = apps_subparsers.add_parser(AppCommands.RELEASE_CHANNELS_LIST.value, help="List release channels of an app")
    release_channels_list_parser.add_argument("app_id", help="ID of the app", type=str)

    # Detail of Release Channel
    release_channel_detail_parser = apps_subparsers.add_parser(AppCommands.RELEASE_CHANNEL_DETAILS.value, help="Detail of a release channel")
    release_channel_detail_parser.add_argument("app_id", help="ID of the app", type=str)
    release_channel_detail_parser.add_argument("--release_channel_id", help="ID of the release channel", type=str)

    # Upload and Create Version
    create_version_parser = apps_subparsers.add_parser(AppCommands.UPLOAD.value, help="Upload a new version of an app")
    create_version_parser.add_argument("app_id", help="ID of the app", type=str)
    create_version_parser.add_argument("filename", help="Local path of the APK to upload", type=str)
    create_version_parser.add_argument("-v", "--version", help="Version Number (APK can override this value)", type=str)
    create_version_parser.add_argument("-n", "--notes", help="Release Notes", type=str)

    # Sharing Apps
    share_parser = apps_subparsers.add_parser(AppCommands.SHARE.value, help="Share an app")
    share_parser.add_argument("app_id", help="ID of the app", type=str)
    share_parser.add_argument("--release_channel_id", help="ID of the release channel to share", type=str, required=True)
    share_parser.add_argument("--organization_slug", help="Slug of the organization to share with", type=str, required=True)

    # Revoke Sharing
    revoke_share_parser = apps_subparsers.add_parser(AppCommands.REVOKE_SHARE.value, help="Revoke sharing of an app")
    revoke_share_parser.add_argument("app_id", help="ID of the app", type=str)
    revoke_share_parser.add_argument("--release_channel_id", help="ID of the release channel to revoke", type=str, required=True)
    revoke_share_parser.add_argument("--organization_slug", help="Slug of the organization to revoke from", type=str, required=True)

    files_parser = subparsers.add_parser("files", help="Files command")
    files_subparsers = files_parser.add_subparsers(dest="files_command", help="Files command help")

    # List All Files
    files_list_parser = files_subparsers.add_parser(FileCommands.LIST.value, help="List files")

    # Detail of File
    file_detail_parser = files_subparsers.add_parser(FileCommands.DETAILS.value, help="Detail of a file")
    file_detail_parser.add_argument("file_id", help="ID of the file", type=str)

    args = parser.parse_args()

    if args.url is None:
        print("API URL is required")
        exit(1)

    if args.token is None:
        print("API Token is required. Please set the ABXR_API_TOKEN environment variable or use the --token command line param.")
        exit(1)

    if args.command == "apps":
        handler = AppsCommandHandler(args)
        handler.run()

    elif args.command == "files":
        handler = FilesCommandHandler(args)
        handler.run()
        

if __name__ == "__main__":
    main()