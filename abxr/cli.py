#!/usr/bin/env python3
#
# Copyright (c) 2024-2025 ABXR Labs, Inc.
# Released under the MIT License. See LICENSE file for details.
#

import warnings
warnings.filterwarnings("ignore", message="urllib3 v2 only supports OpenSSL")

import argparse
import os
from requests import HTTPError

from abxr.version import version
from abxr.formats import DataOutputFormats

from abxr.apps import Commands as AppCommands, CommandHandler as AppsCommandHandler
from abxr.app_bundles import Commands as AppBundlesCommands, CommandHandler as AppBundlesCommandHandler
from abxr.files import Commands as FileCommands, CommandHandler as FilesCommandHandler
from abxr.devices import Commands as DeviceCommands, CommandHandler as DevicesCommandHandler
from abxr.system_apps import Commands as SystemAppCommands, CommandHandler as SystemAppsCommandHandler
from abxr.org import Commands as OrgCommands, CommandHandler as OrgCommandHandler
from abxr.audit_logs import Commands as AuditLogsCommands, CommandHandler as AuditLogsCommandHandler
from abxr.groups import Commands as GroupsCommands, CommandHandler as GroupsCommandHandler
from abxr.tags import Commands as TagsCommands, CommandHandler as TagsCommandHandler
from abxr.users import Commands as UsersCommands, CommandHandler as UsersCommandHandler
from abxr.videos import Commands as VideosCommands, CommandHandler as VideosCommandHandler

ABXR_API_URL = os.environ.get("ABXR_API_URL", "https://api.xrdm.app/api/v2")
ABXR_API_TOKEN = os.environ.get("ABXR_API_TOKEN") or os.environ.get("ARBORXR_ACCESS_TOKEN")


def main():
    parser = argparse.ArgumentParser(description=f'%(prog)s {version}')
    parser.add_argument("-u", "--url", help="API Base URL", type=str, default=ABXR_API_URL)
    parser.add_argument("-t", "--token", help="API Token", type=str, default=ABXR_API_TOKEN)
    parser.add_argument("-f", "--format", help="Data Output format", type=str, choices=[DataOutputFormats.JSON.value, DataOutputFormats.YAML.value], default=DataOutputFormats.YAML.value)
    parser.add_argument("-s", "--silent", help="Hides progress bars or other messages not to interfere with return value processing from stdout", action="store_true")
    parser.add_argument('-v', '--version', action='version', version=f'%(prog)s {version}')

    subparsers = parser.add_subparsers(dest="command", help="Sub-command help")

    # Org
    org_parser = subparsers.add_parser("org", help="Organization command")
    org_subparsers = org_parser.add_subparsers(dest="org_command", help="Organization command help")

    org_info_parser = org_subparsers.add_parser(OrgCommands.INFO.value, help="Get organization info connected to API token")

    # Apps
    apps_parser = subparsers.add_parser("apps", help="Apps command")
    apps_subparsers = apps_parser.add_subparsers(dest="apps_command", help="Apps command help")

    # List All Apps
    apps_list_parser = apps_subparsers.add_parser(AppCommands.LIST.value, help="List apps")

    # Detail of App
    app_detail_parser = apps_subparsers.add_parser(AppCommands.DETAILS.value, help="Get the details of an app")
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
    release_channel_detail_parser.add_argument("--release_channel_id", help="ID of the release channel", type=str, required=True)

    # Set Version for Release Channel
    release_channel_set_version_parser = apps_subparsers.add_parser(AppCommands.RELEASE_CHANNEL_SET_VERSION.value, help="Set version for a release channel")
    release_channel_set_version_parser.add_argument("app_id", help="ID of the app", type=str)
    release_channel_set_version_parser.add_argument("--release_channel_id", help="ID of the release channel", type=str, required=True)
    release_channel_set_version_parser.add_argument("--version_id", help="ID of the version", type=str, required=True)

    # Upload and Create Version
    create_version_parser = apps_subparsers.add_parser(AppCommands.UPLOAD.value, help="Upload a new version of an app")
    create_version_parser.add_argument("app_id", help="ID of the app", type=str)
    create_version_parser.add_argument("filename", help="Local path of the APK/ZIP (apk+obb) to upload", type=str)
    create_version_parser.add_argument("--version_number", help="Version Number (Uploaded APK can override this value)", type=str)
    create_version_parser.add_argument("-n", "--notes", help="Release Notes", type=str)
    create_version_parser.add_argument("-w", "--wait", help="Wait for the upload to complete", action="store_true")
    create_version_parser.add_argument("--wait_time", help="Maximum wait time in seconds for the upload to complete processing", type=int, default=60)

    # Release channel options (mutually exclusive)
    release_channel_group = create_version_parser.add_mutually_exclusive_group()
    release_channel_group.add_argument("--release-channel-id", help="ID of existing release channel to upload to", type=str, dest="release_channel_id")
    release_channel_group.add_argument("--new-release-channel-title", help="Title for a new release channel to create", type=str, dest="new_release_channel_title")

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

    ## Audit Logs
    audit_logs_parser = subparsers.add_parser("audit_logs", help="Audit Logs command")
    audit_logs_subparsers = audit_logs_parser.add_subparsers(dest="audit_logs_command", help="Audit Logs command help")

    # List Audit Logs
    audit_logs_list_parser = audit_logs_subparsers.add_parser(AuditLogsCommands.LIST.value, help="List all audit logs")
    audit_logs_list_parser.add_argument("--search", help="Search term to filter audit logs. Searches across description, user name, user email, resource title, and IP address.", type=str)
    audit_logs_list_parser.add_argument("--start_time", help="Filter audit logs to show only entries created at or after this timestamp (ISO 8601 Zulu format with millisecond precision).", type=str)
    audit_logs_list_parser.add_argument("--end_time", help="Filter audit logs to show only entries created at or before this timestamp (ISO 8601 Zulu format with millisecond precision).", type=str)

    ## Groups
    groups_parser = subparsers.add_parser("groups", help="Groups command")
    groups_subparsers = groups_parser.add_subparsers(dest="groups_command", help="Groups command help")

    # List Groups
    groups_list_parser = groups_subparsers.add_parser(GroupsCommands.LIST.value, help="List all groups")

    # Create a new Group
    groups_add_parser = groups_subparsers.add_parser(GroupsCommands.ADD.value, help="Create a new group")
    groups_add_parser.add_argument("name", help="Name of the group", type=str)
    groups_add_parser.add_argument("--parent_group_id", help="Parent ID of the group to attach to", type=str)

    # Group Detail
    groups_detail_parser = groups_subparsers.add_parser(GroupsCommands.DETAILS.value, help="Get details of a group")
    groups_detail_parser.add_argument("group_id", help="ID of the group", type=str)

    # Group Update
    groups_update_parser = groups_subparsers.add_parser(GroupsCommands.UPDATE.value, help="Update a group")
    groups_update_parser.add_argument("group_id", help="ID of the group", type=str)
    groups_update_parser.add_argument("--name", help="New name of the group", type=str)
    groups_update_parser.add_argument("--parent_group_id", help="New parent ID of the group", type=str)

    # Group Delete
    groups_delete_parser = groups_subparsers.add_parser(GroupsCommands.DELETE.value, help="Delete a group")
    groups_delete_parser.add_argument("group_id", help="ID of the group", type=str)
    groups_delete_parser.add_argument("--replacement_group_id", help="ID of replacement group to move child groups to (only allowed for unconfigured groups)", type=str)

    # Group Configure
    groups_configure_parser = groups_subparsers.add_parser(GroupsCommands.CONFIGURE.value, help="Configure a group (convert from unconfigured to configured state).")
    groups_configure_parser.add_argument("group_id", help="ID of the group", type=str)

    # Group Duplicate
    groups_duplicate_parser = groups_subparsers.add_parser(GroupsCommands.DUPLICATE.value, help="Duplicate a group")
    groups_duplicate_parser.add_argument("group_id", help="ID of the group to duplicate", type=str)
    groups_duplicate_parser.add_argument("--name", help="New name for the duplicated group", type=str, required=True)

    # List Release Channels assigned to a Group
    groups_release_channels_list_parser = groups_subparsers.add_parser(GroupsCommands.RELEASE_CHANNELS_LIST.value, help="List release channels assigned to a group")
    groups_release_channels_list_parser.add_argument("group_id", help="ID of the group", type=str)

    # Assign a Release Channel to a Group
    groups_release_channel_add_parser = groups_subparsers.add_parser(GroupsCommands.RELEASE_CHANNEL_ADD.value, help="Assign a release channel to a group")
    groups_release_channel_add_parser.add_argument("group_id", help="ID of the group", type=str)
    groups_release_channel_add_parser.add_argument("--release_channel_id", help="ID of the release channel to assign", type=str, required=True)

    # Remove a Release Channel from a Group
    groups_release_channel_remove_parser = groups_subparsers.add_parser(GroupsCommands.RELEASE_CHANNEL_REMOVE.value, help="Remove a release channel from a group")
    groups_release_channel_remove_parser.add_argument("group_id", help="ID of the group", type=str)
    groups_release_channel_remove_parser.add_argument("--release_channel_id", help="ID of the release channel to remove", type=str, required=True)

    # Add a File to a Group
    groups_files_add_parser = groups_subparsers.add_parser(GroupsCommands.FILES_ADD.value, help="Add a file to a group")
    groups_files_add_parser.add_argument("group_id", help="ID of the group", type=str)
    groups_files_add_parser.add_argument("--file_id", help="ID of the file to add", type=str, required=True)

    # Remove a File from a Group
    groups_files_remove_parser = groups_subparsers.add_parser(GroupsCommands.FILES_REMOVE.value, help="Remove a file from a group")
    groups_files_remove_parser.add_argument("group_id", help="ID of the group", type=str)
    groups_files_remove_parser.add_argument("--file_id", help="ID of the file to remove", type=str, required=True)

    # Add a Video to a Group
    groups_video_add_parser = groups_subparsers.add_parser(GroupsCommands.VIDEO_ADD.value, help="Add a video to a group")
    groups_video_add_parser.add_argument("group_id", help="ID of the group", type=str)
    groups_video_add_parser.add_argument("--video_id", help="ID of the video to add", type=str, required=True)

    # Remove a Video from a Group
    groups_video_remove_parser = groups_subparsers.add_parser(GroupsCommands.VIDEO_REMOVE.value, help="Remove a video from a group")
    groups_video_remove_parser.add_argument("group_id", help="ID of the group", type=str)
    groups_video_remove_parser.add_argument("--video_id", help="ID of the video to remove", type=str, required=True)

    # Get Group Hierarchy
    groups_hierarchy_detail_parser = groups_subparsers.add_parser(GroupsCommands.HIERARCHY_DETAIL.value, help="Get the full group hierarchy")

    

    ## Files
    files_parser = subparsers.add_parser("files", help="Files command")
    files_subparsers = files_parser.add_subparsers(dest="files_command", help="Files command help")

    # List All Files
    files_list_parser = files_subparsers.add_parser(FileCommands.LIST.value, help="List all files in content library")

    # Detail of File
    file_detail_parser = files_subparsers.add_parser(FileCommands.DETAILS.value, help="Detail of an uploaded file")
    file_detail_parser.add_argument("file_id", help="ID of the file", type=str)

    # Upload a file
    upload_file_parser = files_subparsers.add_parser(FileCommands.UPLOAD.value, help="Upload a file")
    upload_file_parser.add_argument("filename", help="Local path of the file to upload", type=str)
    upload_file_parser.add_argument("--device_path", help="Desired path of the file on the device", type=str, required=True)

    # List All Files Assigned to a Device
    files_device_list_parser = files_subparsers.add_parser(FileCommands.DEVICE_LIST.value, help="List files assigned to a device")
    files_device_list_parser.add_argument("device_id", help="ID of the device", type=str)

    # Assign a File to a Device
    files_device_assign_parser = files_subparsers.add_parser(FileCommands.DEVICE_ASSIGN.value, help="Assign a file to a device")
    files_device_assign_parser.add_argument("device_id", help="ID of the device", type=str)
    files_device_assign_parser.add_argument("--file_id", help="ID of the file to assign", type=str, required=True)

    # Remove a File from a Device
    files_device_remove_parser = files_subparsers.add_parser(FileCommands.DEVICE_REMOVE.value, help="Remove a file from a device")
    files_device_remove_parser.add_argument("device_id", help="ID of the device", type=str)
    files_device_remove_parser.add_argument("--file_id", help="ID of the file to remove", type=str, required=True)

    # Assign a File to a Device Group
    files_device_group_assign_parser = files_subparsers.add_parser(FileCommands.GROUP_ASSIGN.value, help="Assign a file to a group")
    files_device_group_assign_parser.add_argument("group_id", help="ID of the device group", type=str)
    files_device_group_assign_parser.add_argument("--file_id", help="ID of the file to assign", type=str, required=True)

    # Remove a File from a Device Group
    files_device_group_remove_parser = files_subparsers.add_parser(FileCommands.GROUP_REMOVE.value, help="Remove a file from a group")
    files_device_group_remove_parser.add_argument("group_id", help="ID of the device group", type=str)
    files_device_group_remove_parser.add_argument("--file_id", help="ID of the file to remove", type=str, required=True)

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
    launch_app_parser.add_argument("--app_id", help="ID of the app", type=str, required=True)

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
    upload_system_app_parser.add_argument("--version_number", help="Version Number (APK can override this value)", type=str)
    upload_system_app_parser.add_argument("--version_code", help="Version Code (required for OS app type)", type=int)
    upload_system_app_parser.add_argument("-n", "--notes", help="Release Notes", type=str)
    upload_system_app_parser.add_argument("--app_compatibility_name", help="Name of the app compatibility (e.g: armeabi-v7a)", type=str, required=True)
    upload_system_app_parser.add_argument("--release_channel_name", help="Name of the release channel to upload to. Omitting will default to Latest", type=str)
    
    # List Release Channels for System App
    release_channels_list_system_parser = system_apps_subparsers.add_parser(SystemAppCommands.RELEASE_CHANNELS_LIST.value, help="List release channels for a system app")
    release_channels_list_system_parser.add_argument("app_type", help="Type of the system app (e.g., 'client', 'home')", type=str)

    # Detail of Release Channel for System App
    release_channel_detail_system_parser = system_apps_subparsers.add_parser(SystemAppCommands.RELEASE_CHANNEL_DETAILS.value, help="Detail of a release channel for a system app")
    release_channel_detail_system_parser.add_argument("app_type", help="Type of the system app (e.g., 'client', 'home')", type=str)
    release_channel_detail_system_parser.add_argument("--release_channel_id", help="ID of the release channel", type=str, required=True)

    # List App Compatibilities for System App
    app_compatibilities_list_system_parser = system_apps_subparsers.add_parser(SystemAppCommands.APP_COMPATIBILITIES.value, help="List app compatibilities for a system app")
    app_compatibilities_list_system_parser.add_argument("app_type", help="Type of the system app (e.g., 'client', 'home')", type=str)

    # Detail of App Compatibility for System App
    app_compatibility_detail_system_parser = system_apps_subparsers.add_parser(SystemAppCommands.APP_COMPATIBILITY_DETAILS.value, help="Detail of an app compatibility for a system app")
    app_compatibility_detail_system_parser.add_argument("app_type", help="Type of the system app (e.g., 'client', 'home')", type=str)
    app_compatibility_detail_system_parser.add_argument("--app_compatibility_id", help="ID of the app compatibility", type=str, required=True)

    # Tags
    tags_parser = subparsers.add_parser("tags", help="Tags command")
    tags_subparsers = tags_parser.add_subparsers(dest="tags_command", help="Tags command help")

    # List Tags
    tags_list_parser = tags_subparsers.add_parser(TagsCommands.LIST.value, help="List all tags")

    # Create Tag
    tags_create_parser = tags_subparsers.add_parser(TagsCommands.CREATE.value, help="Create a new tag")
    tags_create_parser.add_argument("--name", help="Name of the new tag", type=str, required=True)
   
    # Tag Details
    tags_detail_parser = tags_subparsers.add_parser(TagsCommands.DETAIL.value, help="Get details of a tag")
    tags_detail_parser.add_argument("tag_id", help="ID of the tag", type=str)
   
    # Update Tag
    tags_update_parser = tags_subparsers.add_parser(TagsCommands.UPDATE.value, help="Update a tag")
    tags_update_parser.add_argument("tag_id", help="ID of the tag", type=str)
    tags_update_parser.add_argument("--name", help="New name for the tag", type=str, required=True)
   
    # Delete Tag
    tags_delete_parser = tags_subparsers.add_parser(TagsCommands.DELETE.value, help="Delete a tag")
    tags_delete_parser.add_argument("tag_id", help="ID of the tag", type=str)

    # Users
    users_parser = subparsers.add_parser("users", help="Users command")
    users_subparsers = users_parser.add_subparsers(dest="users_command", help="Users command help")

    # List Users
    users_list_parser = users_subparsers.add_parser(UsersCommands.LIST.value, help="List all users")

    # Create User
    users_create_parser = users_subparsers.add_parser(UsersCommands.CREATE.value, help="Create a new user")
    users_create_parser.add_argument("--first_name", help="First name of the new user", type=str, required=True)
    users_create_parser.add_argument("--last_name", help="Last name of the new user", type=str, required=True)
    users_create_parser.add_argument("--email", help="Email of the new user", type=str, required=True)

    # User Details
    users_detail_parser = users_subparsers.add_parser(UsersCommands.DETAILS.value, help="Get details of a user")
    users_detail_parser.add_argument("user_id", help="ID of the user", type=str)

    # Update User
    users_update_parser = users_subparsers.add_parser(UsersCommands.UPDATE.value, help="Update a user")
    users_update_parser.add_argument("user_id", help="ID of the user", type=str)
    users_update_parser.add_argument("--first_name", help="New first name for the user", type=str)
    users_update_parser.add_argument("--last_name", help="New last name for the user", type=str)

    # Delete User
    users_delete_parser = users_subparsers.add_parser(UsersCommands.DELETE.value, help="Delete a user")
    users_delete_parser.add_argument("user_id", help="ID of the user", type=str)

    # Videos
    videos_parser = subparsers.add_parser("videos", help="Videos command")
    videos_subparsers = videos_parser.add_subparsers(dest="videos_command", help="Videos command help")

    # List All Videos
    videos_list_parser = videos_subparsers.add_parser(VideosCommands.LIST.value, help="List all videos")

    # Video Detail
    videos_detail_parser = videos_subparsers.add_parser(VideosCommands.DETAILS.value, help="Get details of a video")
    videos_detail_parser.add_argument("video_id", help="ID of the video", type=str)

    # Update Video
    videos_update_parser = videos_subparsers.add_parser(VideosCommands.UPDATE, help="Update the properties of a video")
    videos_update_parser.add_argument("video_id", help="ID of the video", type=str)
    videos_update_parser.add_argument("--name", help="Name of the video", type=str)
    videos_update_parser.add_argument("--description", help="Description of the video", type=str)
    videos_update_parser.add_argument("--video_type", help="Type of the video", type=str, choices=["ThreeSixty", "OneEighty", "TwoDimensional"])
    videos_update_parser.add_argument("--video_mapping", help="Mapping of the video", type=str, choices=["EQUIRECTANGULAR", "CUBEMAP"])
    videos_update_parser.add_argument("--video_display", help="Display of the video", type=str, choices=["Stereoscopic", "Monoscopic"])
    videos_update_parser.add_argument("--video_packing", help="Packing of the video", type=str, choices=["TOP_BOTTOM", "LEFT_RIGHT"])
    videos_update_parser.add_argument("--audio_encoding", help="Audio Encoding", type=str, choices=["UNKNOWN", "MONO", "STEREO", "TBE_8", "TBE_8_2", "TBE_6", "TBE_6_2", "TBE_4", "TBE_4_2", "TBE_8_PAIR_0", "TBE_8_PAIR_1", "TBE_8_PAIR_2", "TBE_8_PAIR_3", "TBE_CHANNEL_0", "TBE_CHANNEL_1", "TBE_CHANNEL_2", "TBE_CHANNEL_3", "TBE_CHANNEL_4", "TBE_CHANNEL_5", "TBE_CHANNEL_6", "TBE_CHANNEL_7", "HEADLOCKED_STEREO", "HEADLOCKED_CHANNEL_0", "HEADLOCKED_CHANNEL_1", "AMBIX_4", "AMBIX_4_2", "AMBIX_9", "AMBIX_9_2", "AMBIX_16", "AMBIX_16_2"])
    videos_update_parser.add_argument("--tags", help="Tags to add to the video", type=list)

    # Upload New Video
    videos_upload_parser = videos_subparsers.add_parser(VideosCommands.UPLOAD.value, help="Upload a new video")
    videos_upload_parser.add_argument("filename", help="Local path of the video file to upload", type=str)
    videos_upload_parser.add_argument("--video_type", help="Type of the video", type=str, choices=["ThreeSixty", "OneEighty", "TwoDimensional"], required=True)
    videos_upload_parser.add_argument("--video_mapping", help="Mapping of the video", type=str, choices=["EQUIRECTANGULAR", "CUBEMAP"])
    videos_upload_parser.add_argument("--video_display", help="Display of the video", type=str, choices=["Stereoscopic", "Monoscopic"])
    videos_upload_parser.add_argument("--video_packing", help="Packing of the video", type=str, choices=["TOP_BOTTOM", "LEFT_RIGHT"])
    videos_upload_parser.add_argument("--audio_encoding", help="Audio Encoding", type=str, choices=["UNKNOWN", "MONO", "STEREO", "TBE_8", "TBE_8_2", "TBE_6", "TBE_6_2", "TBE_4", "TBE_4_2", "TBE_8_PAIR_0", "TBE_8_PAIR_1", "TBE_8_PAIR_2", "TBE_8_PAIR_3", "TBE_CHANNEL_0", "TBE_CHANNEL_1", "TBE_CHANNEL_2", "TBE_CHANNEL_3", "TBE_CHANNEL_4", "TBE_CHANNEL_5", "TBE_CHANNEL_6", "TBE_CHANNEL_7", "HEADLOCKED_STEREO", "HEADLOCKED_CHANNEL_0", "HEADLOCKED_CHANNEL_1", "AMBIX_4", "AMBIX_4_2", "AMBIX_9", "AMBIX_9_2", "AMBIX_16", "AMBIX_16_2"])

    # Attach Tags to a video
    videos_attach_tags_parser = videos_subparsers.add_parser(VideosCommands.ATTACH_TAGS.value, help="Attach tags to a video")
    videos_attach_tags_parser.add_argument("video_id", help="ID of the video", type=str)
    videos_attach_tags_parser.add_argument("--tags", help="Tags to add to the video", type=list, required=True)

    # Detach Tags from a video
    videos_detach_tags_parser = videos_subparsers.add_parser(VideosCommands.DETACH_TAGS, help="Detach tags from a video")
    videos_detach_tags_parser.add_argument("video_id", help="ID of the video", type=str)
    videos_detach_tags_parser.add_argument("--tags", help="Tags to remove from the video", type=list, required=True)

    # App Bundles
    app_bundles_parser = subparsers.add_parser("app_bundles", help="App Bundles command")
    app_bundles_subparsers = app_bundles_parser.add_subparsers(dest="app_bundles_command", help="App Bundles command help")

    # Upload an app bundle
    app_bundles_upload_parser = app_bundles_subparsers.add_parser(AppBundlesCommands.UPLOAD.value, help="Upload an app bundle with APK and files (bundle labels are auto-generated)")
    app_bundles_upload_parser.add_argument("app_id", help="ID of the app", type=str)
    app_bundles_upload_parser.add_argument("apk_path", help="Path to APK file", type=str)
    app_bundles_upload_parser.add_argument("bundle_folder", help="Path to folder containing bundle files", type=str)
    app_bundles_upload_parser.add_argument("--version_number", help="Version number (APK can override this value)", type=str)
    app_bundles_upload_parser.add_argument("-n", "--notes", help="Release notes for the bundle", type=str)
    app_bundles_upload_parser.add_argument("--device_path", help="Optional device path relative to /sdcard for bundle files", type=str)
    app_bundles_upload_parser.add_argument("-s", "--silent", help="Suppress progress bars and other output", action="store_true")

    # Release channel options (mutually exclusive)
    bundle_release_channel_group = app_bundles_upload_parser.add_mutually_exclusive_group()
    bundle_release_channel_group.add_argument("--release-channel-id", help="ID of existing release channel to upload to", type=str, dest="release_channel_id")
    bundle_release_channel_group.add_argument("--new-release-channel-title", help="Title for a new release channel to create", type=str, dest="new_release_channel_title")

    # List app bundles for an app
    app_bundles_list_parser = app_bundles_subparsers.add_parser(AppBundlesCommands.LIST.value, help="List app bundles for an app")
    app_bundles_list_parser.add_argument("app_id", help="ID of the app", type=str)
    app_bundles_list_parser.add_argument("--status", help="Filter by status (pending, processing, failed, available)", type=str)

    # Get app bundle details
    app_bundles_details_parser = app_bundles_subparsers.add_parser(AppBundlesCommands.DETAILS.value, help="Get details of an app bundle")
    app_bundles_details_parser.add_argument("app_bundle_id", help="ID of the app bundle", type=str)

    # Resume a failed or interrupted app bundle upload
    app_bundles_resume_parser = app_bundles_subparsers.add_parser(AppBundlesCommands.RESUME.value, help="Resume a failed or interrupted bundle upload")
    app_bundles_resume_parser.add_argument("bundle_id", help="ID of the bundle to resume", type=str)
    app_bundles_resume_parser.add_argument("apk_path", help="Path to APK file", type=str)
    app_bundles_resume_parser.add_argument("folder_path", help="Path to folder with bundle files", type=str)
    app_bundles_resume_parser.add_argument("--device_path", help="Optional device path relative to /sdcard for bundle files (must match original upload)", type=str)
    app_bundles_resume_parser.add_argument("-s", "--silent", help="Suppress progress bars and other output", action="store_true")

    # Update an app bundle's label
    app_bundles_update_label_parser = app_bundles_subparsers.add_parser(AppBundlesCommands.UPDATE_LABEL.value, help="Update an app bundle's label")
    app_bundles_update_label_parser.add_argument("app_bundle_id", help="ID of the app bundle", type=str)
    label_group = app_bundles_update_label_parser.add_mutually_exclusive_group(required=True)
    label_group.add_argument("--label", help="New label for the bundle (max 60 characters)", type=str)
    label_group.add_argument("--clear", help="Remove the label from the bundle", action="store_true")

    # Create app bundle from existing build
    app_bundles_create_from_build_parser = app_bundles_subparsers.add_parser(AppBundlesCommands.CREATE_FROM_BUILD.value, help="Create an app bundle from an existing build ID and folder of files")
    app_bundles_create_from_build_parser.add_argument("build_id", help="ID of the existing app build/version", type=str)
    app_bundles_create_from_build_parser.add_argument("bundle_folder", help="Path to folder containing bundle files", type=str)
    app_bundles_create_from_build_parser.add_argument("app_id", help="ID of the app (needed for file deduplication)", type=str)
    app_bundles_create_from_build_parser.add_argument("--device_path", help="Optional device path relative to /sdcard for bundle files", type=str)
    app_bundles_create_from_build_parser.add_argument("-s", "--silent", help="Suppress progress bars and other output", action="store_true")

    # Release channel options (mutually exclusive)
    create_from_build_release_channel_group = app_bundles_create_from_build_parser.add_mutually_exclusive_group()
    create_from_build_release_channel_group.add_argument("--release-channel-id", help="ID of existing release channel to associate with bundle", type=str, dest="release_channel_id")
    create_from_build_release_channel_group.add_argument("--new-release-channel-title", help="Title for a new release channel to create", type=str, dest="new_release_channel_title")

    args = parser.parse_args()

    if args.url is None:
        print("API URL is required")
        exit(1)

    if args.token is None:
        print("API Token is required. Please set the ABXR_API_TOKEN environment variable or use the --token command line param.")
        exit(1)

    try:
        if args.command == "apps":
            handler = AppsCommandHandler(args)
            handler.run()

        elif args.command == "audit_logs":
            handler = AuditLogsCommandHandler(args)
            handler.run()

        elif args.command == "files":
            handler = FilesCommandHandler(args)
            handler.run()

        elif args.command == "devices":
            handler = DevicesCommandHandler(args)
            handler.run()

        elif args.command == "groups":
            handler = GroupsCommandHandler(args)
            handler.run()

        elif args.command == "system_apps":
            handler = SystemAppsCommandHandler(args)
            handler.run()

        elif args.command == "org":
            handler = OrgCommandHandler(args)
            handler.run()

        elif args.command == "tags":
            handler = TagsCommandHandler(args)
            handler.run()

        elif args.command == "users":
            handler = UsersCommandHandler(args)
            handler.run()

        elif args.command == "videos":
            handler = VideosCommandHandler(args)
            handler.run()

        elif args.command == "app_bundles":
            handler = AppBundlesCommandHandler(args)
            handler.run()

    except HTTPError as e:
        if e.response is not None and e.response.status_code == 401:
            print("Unauthorized: Invalid API Token.")
            exit(1)
        else:
            print(f"HTTP Error: {e}")
            exit(1)
    
    except Exception as e:
        print(f"Error: {e}")
        exit(1)
        

if __name__ == "__main__":
    main()