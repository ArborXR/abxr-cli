#!/usr/bin/env python3
#
# Copyright (c) 2024-2025 ABXR Labs, Inc.
# Released under the MIT License. See LICENSE file for details.
#

from enum import Enum

from abxr.api_service import ApiService
from abxr.formats import DataOutputFormats
from abxr.output import print_formatted

class Commands(Enum):
    LIST = "list"
    ADD = "add"
    DETAILS = "details"
    UPDATE = "update"
    DELETE = "delete"
    CONFIGURE = "configure"
    DUPLICATE = "duplicate"
    RELEASE_CHANNELS_LIST = "release_channels"
    RELEASE_CHANNEL_ADD = "add_release_channel"
    RELEASE_CHANNEL_REMOVE = "remove_release_channel"
    FILES_ADD = "add_file"
    FILES_REMOVE = "remove_file"
    VIDEO_ADD = "add_video"
    VIDEO_REMOVE = "remove_video"
    HIERARCHY_DETAIL = "tree"


class GroupsService(ApiService):
    def __init__(self, base_url, token):
        super().__init__(base_url, token)

    def get_all_groups(self):
        url = f'{self.base_url}/groups?per_page=20'

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

    def create_group(self, group_name, parent_id=None):
        url = f'{self.base_url}/groups'
        payload = {
            "name": group_name,
            "parent_id": parent_id
        }

        response = self.client.post(url, headers=self.headers, json=payload)
        response.raise_for_status()

        return response.json()

    def get_group_details(self, group_id):
        url = f'{self.base_url}/groups/{group_id}'

        response = self.client.get(url, headers=self.headers)
        response.raise_for_status()

        return response.json()

    def update_group(self, group_id, group_name, parent_id=None):
        url = f'{self.base_url}/groups/{group_id}'

        payload = {
            "name": group_name,
            "parent_id": parent_id
        }

        response = self.client.put(url, headers=self.headers, json=payload)
        response.raise_for_status()

        return response.json()
    
    def delete_group(self, group_id):
        url = f'{self.base_url}/groups/{group_id}'

        response = self.client.delete(url, headers=self.headers)
        response.raise_for_status()

        return response.json()
    
    def configure_group(self, group_id):
        url = f'{self.base_url}/groups/{group_id}/configure'

        response = self.client.patch(url, headers=self.headers)
        response.raise_for_status()

        return response.json()
    
    def duplicate_group(self, group_id, new_group_name):
        url = f'{self.base_url}/groups/{group_id}/duplicate'

        payload = {
            "name": new_group_name
        }

        response = self.client.post(url, headers=self.headers, json=payload)
        response.raise_for_status()

        return response.json()
    
    def get_group_release_channels(self, group_id):
        url = f'{self.base_url}/groups/{group_id}/release-channels?per_page=20'

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
    
    def add_group_release_channel(self, group_id, release_channel_id):
        url = f'{self.base_url}/groups/{group_id}/release-channels'
        payload = {
            "releaseChannelId": release_channel_id
        }

        response = self.client.post(url, headers=self.headers, json=payload)
        response.raise_for_status()

        return response.json()
    
    def remove_release_channel_from_group(self, group_id, release_channel_id):
        url = f'{self.base_url}/groups/{group_id}/release-channels/{release_channel_id}'

        response = self.client.delete(url, headers=self.headers)
        response.raise_for_status()

        return response.json()
    
    def add_file_to_group(self, group_id, file_id):
        url = f'{self.base_url}/groups/{group_id}/files'
        data = { 'fileId': file_id }

        response = self.client.post(url, json=data, headers=self.headers)
        response.raise_for_status()
        
        return response.json()
    
    def remove_file_from_group(self, group_id, file_id):
        url = f'{self.base_url}/groups/{group_id}/files'
        data = { 'fileId': file_id }

        response = self.client.delete(url, json=data, headers=self.headers)
        response.raise_for_status()
        
        return response.json()
    
    def add_video_to_group(self, group_id, video_id):
        url = f'{self.base_url}/groups/{group_id}/videos'
        data = { 'videoId': video_id }

        response = self.client.post(url, json=data, headers=self.headers)
        response.raise_for_status()
        
        return response.json()
    
    def remove_video_from_group(self, group_id, video_id):
        url = f'{self.base_url}/groups/{group_id}/videos'
        data = { 'videoId': video_id }

        response = self.client.delete(url, json=data, headers=self.headers)
        response.raise_for_status()
        
        return response.json()
    
    def get_group_hierarchy(self):
        url = f'{self.base_url}/group-hierarchy'

        response = self.client.get(url, headers=self.headers)
        response.raise_for_status()

        return response.json()
    



class CommandHandler:
    def __init__(self, args):
        self.args = args
        self.service = GroupsService(self.args.url, self.args.token)

    def run(self):
        if self.args.groups_command == Commands.LIST.value:            
            groups = self.service.get_all_groups()
            print_formatted(self.args.format, groups)

        elif self.args.groups_command == Commands.ADD.value:
            group_detail = self.service.create_group(self.args.name, self.args.parent_group_id)
            print_formatted(self.args.format, group_detail)

        elif self.args.groups_command == Commands.DETAILS.value:
            group_detail = self.service.get_group_details(self.args.group_id)
            print_formatted(self.args.format, group_detail)

        elif self.args.groups_command == Commands.UPDATE.value:
            group_detail = self.service.update_group(self.args.group_id, self.args.name, self.args.parent_group_id)
            print_formatted(self.args.format, group_detail)

        elif self.args.groups_command == Commands.DELETE.value:
            self.service.delete_group(self.args.group_id)

        elif self.args.groups_command == Commands.CONFIGURE.value:
            group_detail = self.service.configure_group(self.args.group_id)
            print_formatted(self.args.format, group_detail)

        elif self.args.groups_command == Commands.DUPLICATE.value:
            group_detail = self.service.duplicate_group(self.args.group_id, self.args.new_name)
            print_formatted(self.args.format, group_detail)

        elif self.args.groups_command == Commands.RELEASE_CHANNELS_LIST.value:
            release_channels = self.service.get_group_release_channels(self.args.group_id)
            print_formatted(self.args.format, release_channels)

        elif self.args.groups_command == Commands.RELEASE_CHANNEL_ADD.value:
            group_detail = self.service.add_group_release_channel(self.args.group_id, self.args.release_channel_id)
            print_formatted(self.args.format, group_detail)

        elif self.args.groups_command == Commands.RELEASE_CHANNEL_REMOVE.value:
            self.service.remove_release_channel_from_group(self.args.group_id, self.args.release_channel_id)

        elif self.args.groups_command == Commands.FILES_ADD.value:
            group_detail = self.service.add_file_to_group(self.args.group_id, self.args.file_id)
            print_formatted(self.args.format, group_detail)

        elif self.args.groups_command == Commands.FILES_REMOVE.value:
            self.service.remove_file_from_group(self.args.group_id, self.args.file_id)

        elif self.args.groups_command == Commands.VIDEO_ADD.value:
            group_detail = self.service.add_video_to_group(self.args.group_id, self.args.video_id)
            print_formatted(self.args.format, group_detail)

        elif self.args.groups_command == Commands.VIDEO_REMOVE.value:
            self.service.remove_video_from_group(self.args.group_id, self.args.video_id)

        elif self.args.groups_command == Commands.HIERARCHY_DETAIL.value:
            hierarchy = self.service.get_group_hierarchy()
            print_formatted(self.args.format, hierarchy)


