#!/usr/bin/env python3
#
# Copyright (c) 2024-2025 ABXR Labs, Inc.
# Released under the MIT License. See LICENSE file for details.
#

from tqdm import tqdm

from enum import Enum

from abxr.api_service import ApiService
from abxr.formats import DataOutputFormats

from abxr.output import print_formatted

class Commands(Enum):
    LIST = "list"
    DETAILS = "details"
    LAUNCH_APP = "launch"
    REBOOT = "reboot"
    SHUTDOWN = "shutdown"
    FACTORY_RESET = "factory_reset"

    RELEASE_CHANNELS_LIST = "release_channels"
    RELEASE_CHANNEL_ADD = "add_release_channel"
    RELEASE_CHANNEL_REMOVE = "remove_release_channel"
    FILES_LIST = "list_files"
    FILES_ADD = "add_file"
    FILES_REMOVE = "remove_file"
    VIDEOS_LIST = "list_videos"
    VIDEOS_ADD = "add_video"
    VIDEOS_REMOVE = "remove_video"

    MIGRATE_TO_ORG = "migrate_to_org"

    ATTACH_TAGS = "attach_tags"
    DETACH_TAGS = "detach_tags"

class DevicesService(ApiService):
    def __init__(self, base_url, token):
        super().__init__(base_url, token)
        
    def get_all_devices(self):
        url = f'{self.base_url}/devices?per_page=20'

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
    
    def get_device_detail(self, device_id):
        url = f'{self.base_url}/devices/{device_id}'

        response = self.client.get(url, headers=self.headers)
        response.raise_for_status()

        return response.json()
    
    def launch_app(self, device_id, app_id):
        url = f'{self.base_url}/devices/{device_id}/launch/{app_id}'

        response = self.client.post(url, headers=self.headers)
        response.raise_for_status()

        return response.json()
    
    def reboot_device(self, device_id):
        url = f'{self.base_url}/devices/{device_id}/reboot'
        
        response = self.client.post(url, headers=self.headers)
        response.raise_for_status()
        
        return response.json()
    
    def shutdown_device(self, device_id):
        url = f'{self.base_url}/devices/{device_id}/shutdown'

        response = self.client.post(url, headers=self.headers)
        response.raise_for_status()

        return response.json()
    
    def factory_reset_device(self, device_id):
        url = f'{self.base_url}/devices/{device_id}/factory-reset'

        response = self.client.post(url, headers=self.headers)
        response.raise_for_status()

        return response.json()
    
    def list_release_channels_for_device(self, device_id):
        url = f'{self.base_url}/devices/{device_id}/release-channels?per_page=20'

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
    
    def add_release_channel_to_device(self, device_id, release_channel_id):
        url = f'{self.base_url}/devices/{device_id}/release-channels'

        data = {
            'releaseChannelId': release_channel_id
        }

        response = self.client.post(url, json=data, headers=self.headers)
        response.raise_for_status()
        
        return response.json()

    def remove_release_channel_from_device(self, device_id, release_channel_id):
        url = f'{self.base_url}/devices/{device_id}/release-channels'

        data = {
            'releaseChannelId': release_channel_id
        }

        response = self.client.delete(url, json=data, headers=self.headers)
        response.raise_for_status()
        
        return response.json()
    
    def list_files_for_device(self, device_id):
        url = f'{self.base_url}/devices/{device_id}/files?per_page=20'

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
    
    def add_file_to_device(self, device_id, file_id):
        url = f'{self.base_url}/devices/{device_id}/files'

        data = {
            'fileId': file_id
        }

        response = self.client.post(url, json=data, headers=self.headers)
        response.raise_for_status()
        
        return response.json()
    
    def remove_file_from_device(self, device_id, file_id):
        url = f'{self.base_url}/devices/{device_id}/files'

        data = {
            'fileId': file_id
        }

        response = self.client.delete(url, json=data, headers=self.headers)
        response.raise_for_status()
        
        return response.json()
    
    def list_videos_for_device(self, device_id):
        url = f'{self.base_url}/devices/{device_id}/videos?per_page=20'

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
    
    def add_video_to_device(self, device_id, video_id):
        url = f'{self.base_url}/devices/{device_id}/videos'

        data = {
            'videoId': video_id
        }

        response = self.client.post(url, json=data, headers=self.headers)
        response.raise_for_status()
        
        return response.json()
    
    def remove_video_from_device(self, device_id, video_id):
        url = f'{self.base_url}/devices/{device_id}/videos'

        data = {
            'videoId': video_id
        }

        response = self.client.delete(url, json=data, headers=self.headers)
        response.raise_for_status()

        return response.json()

    def migrate_device_to_org(self, device_id, new_organization_slug, new_organization_token, new_organization_group_id):
        url = f'{self.base_url}/devices/{device_id}/migrate/{new_organization_slug}'

        data = {
            'targetOrganizationToken': new_organization_token,
            'groupId': new_organization_group_id
        }

        response = self.client.post(url, json=data, headers=self.headers)
        response.raise_for_status()

        return response.json()
    
    def attach_tags_to_device(self, device_id, tags):
        url = f'{self.base_url}/devices/{device_id}/tags/attach'

        data = {
            'tags': tags
        }

        response = self.client.post(url, json=data, headers=self.headers)
        response.raise_for_status()

        return response.json()
    
    def detach_tags_from_device(self, device_id, tags):
        url = f'{self.base_url}/devices/{device_id}/tags/detach'

        data = {
            'tags': tags
        }

        response = self.client.post(url, json=data, headers=self.headers)
        response.raise_for_status()

        return response.json()



class CommandHandler:
    def __init__(self, args):
        self.args = args
        self.service = DevicesService(self.args.url, self.args.token)

    def run(self):
        if self.args.devices_command == Commands.LIST.value:            
            devices_list = self.service.get_all_devices()
            print_formatted(self.args.format, devices_list)

        elif self.args.devices_command == Commands.DETAILS.value:
            device_detail = self.service.get_device_detail(self.args.device_id)
            print_formatted(self.args.format, device_detail)

        elif self.args.devices_command == Commands.LAUNCH_APP.value:
            self.service.launch_app(self.args.device_id, self.args.app_id)

        elif self.args.devices_command == Commands.REBOOT.value:
            self.service.reboot_device(self.args.device_id)

        elif self.args.devices_command == Commands.SHUTDOWN.value:
            self.service.shutdown_device(self.args.device_id)

        elif self.args.devices_command == Commands.FACTORY_RESET.value:
            self.service.factory_reset_device(self.args.device_id)

        elif self.args.devices_command == Commands.RELEASE_CHANNELS_LIST:
            device_release_channels_list = self.service.list_release_channels_for_device(self.args.device_id)
            print_formatted(self.args.format, device_release_channels_list)

        elif self.args.devices_command == Commands.RELEASE_CHANNEL_ADD:
            self.service.add_release_channel_to_device(self.args.device_id, self.args.release_channel_id)

        elif self.args.devices_command == Commands.RELEASE_CHANNEL_REMOVE:
            self.service.remove_release_channel_from_device(self.args.device_id, self.args.release_channel_id)
        
        elif self.args.devices_command == Commands.FILES_LIST:
            device_files_list = self.service.list_files_for_device(self.args.device_id)
            print_formatted(self.args.format, device_files_list)

        elif self.args.devices_command == Commands.FILES_ADD:
            self.service.add_file_to_device(self.args.device_id, self.args.file_id)

        elif self.args.devices_command == Commands.FILES_REMOVE:
            self.service.remove_file_from_device(self.args.device_id, self.args.file_id)

        elif self.args.devices_command == Commands.VIDEOS_LIST:
            device_videos_list = self.service.list_videos_for_device(self.args.device_id)
            print_formatted(self.args.format, device_videos_list)

        elif self.args.devices_command == Commands.VIDEOS_ADD:
            self.service.add_video_to_device(self.args.device_id, self.args.video_id)

        elif self.args.devices_command == Commands.VIDEOS_REMOVE:
            self.service.remove_video_from_device(self.args.device_id, self.args.video_id)

        elif self.args.devices_command == Commands.MIGRATE_TO_ORG:
            self.service.migrate_device_to_org(self.args.device_id, self.args.new_organization_slug, self.args.new_organization_token, self.args.new_organization_group_id)





