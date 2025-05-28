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
from abxr.devices import Commands as DeviceCommands, CommandHandler as DevicesCommandHandler
from abxr.system_apps import Commands as SystemAppCommands, CommandHandler as SystemAppsCommandHandler

ABXR_API_URL = os.environ.get("ABXR_API_URL", "https://api.xrdm.app/api/v2")
ABXR_API_TOKEN = os.environ.get("ABXR_API_TOKEN") or os.environ.get("ARBORXR_ACCESS_TOKEN")


def main():
    parser = argparse.ArgumentParser(description=f'%(prog)s {version}')
    parser.add_argument("-u", "--url", help="API Base URL", type=str, default=ABXR_API_URL)
    parser.add_argument("-t", "--token", help="API Token", type=str, default=ABXR_API_TOKEN)
    parser.add_argument("-f", "--format", help="Data Output format", type=str, choices=[DataOutputFormats.JSON.value, DataOutputFormats.YAML.value], default=DataOutputFormats.YAML.value)
    parser.add_argument("-s", "--silent", help="Hides progress bars or other messages not to intefere with return value processing from stdout", action="store_true")
    parser.add_argument('-v', '--version', action='version', version=f'%(prog)s {version}')

    subparsers = parser.add_subparsers(dest="command", help="Sub-command help")

    apps_parser = subparsers.add_parser("apps", help="Apps command")
    apps_subparsers = apps_parser.add_subparsers(dest="apps_command", help="Apps command help")

    # List All Apps
    apps_list_parser = apps_subparsers.add_parser(AppCommands.LIST.value, help="List apps")

    # Detail of App
    app_detail_parser = apps_subparsers.add_parser(AppCommands.DETAILS.value, help="Detail of an app")
    app_detail_parser.add_argument("app_id", help="ID of the app", type=str)

    # Versions of an App
    versions_list_parser = apps_subparsers.add_parser(AppCommands.VERSION_LIST.value, help="List versions of an app")
    versions_list_parser.add_argument("app_id", help="ID of the app", type=str)


    # List Release Channels
    release_channels_list_parser = apps_subparsers.add_parser(AppCommands.RELEASE_CHANNELS_LIST.value, help="List release channels of an app")
    release_channels_list_parser.add_argument("app_id", help="ID of the app", type=str)

    # Detail of Release Channel
    release_channel_detail_parser = apps_subparsers.add_parser(AppCommands.RELEASE_CHANNEL_DETAILS.value, help="Detail of a release channel")
    release_channel_detail_parser.add_argument("app_id", help="ID of the app", type=str)
    release_channel_detail_parser.add_argument("--release_channel_id", help="ID of the release channel", type=str)

    # Set Version for Release Channel
    release_channel_set_version_parser = apps_subparsers.add_parser(AppCommands.RELEASE_CHANNEL_SET_VERSION.value, help="Set version for a release channel")
    release_channel_set_version_parser.add_argument("app_id", help="ID of the app", type=str)
    release_channel_set_version_parser.add_argument("--release_channel_id", help="ID of the release channel", type=str)
    release_channel_set_version_parser.add_argument("--version_id", help="ID of the version", type=str)

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

    # Upload a file
    upload_file_parser = files_subparsers.add_parser(FileCommands.UPLOAD.value, help="Upload a file")
    upload_file_parser.add_argument("filename", help="Local path of the file to upload", type=str)
    upload_file_parser.add_argument("-p", "--path", help="Path of the file on the device", type=str)

    # Devices
    devices_parser = subparsers.add_parser("devices", help="Devices command")
    devices_subparsers = devices_parser.add_subparsers(dest="devices_command", help="Devices command help")

    # List All Devices
    devices_list_parser = devices_subparsers.add_parser(DeviceCommands.LIST.value, help="List devices")

    # Detail of Device
    device_detail_parser = devices_subparsers.add_parser(DeviceCommands.DETAILS.value, help="Detail of a device")
    device_detail_parser.add_argument("device_id", help="ID of the device", type=str)

    # Launch App on Device
    launch_app_parser = devices_subparsers.add_parser(DeviceCommands.LAUNCH_APP.value, help="Launch an app on a device")
    launch_app_parser.add_argument("device_id", help="ID of the device", type=str)
    launch_app_parser.add_argument("--app_id", help="ID of the app", type=str)

    # Reboot Device
    reboot_device_parser = devices_subparsers.add_parser(DeviceCommands.REBOOT.value, help="Reboot a device")
    reboot_device_parser.add_argument("device_id", help="ID of the device", type=str)

    # System Apps
    system_apps_parser = subparsers.add_parser("system_apps", help="System Apps command")
    system_apps_subparsers = system_apps_parser.add_subparsers(dest="system_apps_command", help="System Apps command help")

    # List All System App Versions
    system_apps_list_parser = system_apps_subparsers.add_parser(SystemAppCommands.VERSIONS_LIST.value, help="List system app versions")
    system_apps_list_parser.add_argument("app_type", help="Type of the system app (e.g., 'client', 'home')", type=str)

    # Upload System App
    upload_system_app_parser = system_apps_subparsers.add_parser(SystemAppCommands.UPLOAD.value, help="Upload a system app")
    upload_system_app_parser.add_argument("app_type", help="Type of the system app (e.g., 'client', 'home')", type=str)
    upload_system_app_parser.add_argument("filename", help="Local path of the APK to upload", type=str)
    upload_system_app_parser.add_argument("-v", "--version", help="Version Number (APK can override this value)", type=str)
    upload_system_app_parser.add_argument("-n", "--notes", help="Release Notes", type=str)
    upload_system_app_parser.add_argument("--release_channel_id", help="ID of the release channel to upload to", type=str)
    upload_system_app_parser.add_argument("--release_channel_name", help="Name of the release channel to upload to", type=str)
    upload_system_app_parser.add_argument("--app_compatibility_id", help="ID of the app compatibility to upload to", type=str)
    
    # List Release Channels for System App
    release_channels_list_system_parser = system_apps_subparsers.add_parser(SystemAppCommands.RELEASE_CHANNELS_LIST.value, help="List release channels for a system app")
    release_channels_list_system_parser.add_argument("app_type", help="Type of the system app (e.g., 'client', 'home')", type=str)

    # Detail of Release Channel for System App
    release_channel_detail_system_parser = system_apps_subparsers.add_parser(SystemAppCommands.RELEASE_CHANNEL_DETAILS.value, help="Detail of a release channel for a system app")
    release_channel_detail_system_parser.add_argument("app_type", help="Type of the system app (e.g., 'client', 'home')", type=str)
    release_channel_detail_system_parser.add_argument("--release_channel_id", help="ID of the release channel", type=str)

    # List App Compatibilities for System App
    app_compatibilities_list_system_parser = system_apps_subparsers.add_parser(SystemAppCommands.APP_COMPATIBILITIES.value, help="List app compatibilities for a system app")
    app_compatibilities_list_system_parser.add_argument("app_type", help="Type of the system app (e.g., 'client', 'home')", type=str)

    # Detail of App Compatibility for System App
    app_compatibility_detail_system_parser = system_apps_subparsers.add_parser(SystemAppCommands.APP_COMPATIBILITY_DETAILS.value, help="Detail of an app compatibility for a system app")
    app_compatibility_detail_system_parser.add_argument("app_type", help="Type of the system app (e.g., 'client', 'home')", type=str)
    app_compatibility_detail_system_parser.add_argument("--app_compatibility_id", help="ID of the app compatibility", type=str)

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

    elif args.command == "devices":
        handler = DevicesCommandHandler(args)
        handler.run()

    elif args.command == "system_apps":
        handler = SystemAppsCommandHandler(args)
        handler.run()
        

if __name__ == "__main__":
    main()