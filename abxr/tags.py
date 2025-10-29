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
    CREATE = "create"
    DETAIL = "detail"
    UPDATE = "update"
    DELETE = "delete"


class TagsService(ApiService):
    def __init__(self, base_url, token):
        super().__init__(base_url, token)

    def get_all_tags(self):
        url = f'{self.base_url}/tags?per_page=20'

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
    
    def create_tag(self, tag_name):
        url = f'{self.base_url}/tags'
        payload = {
            "name": tag_name
        }

        response = self.client.post(url, headers=self.headers, json=payload)
        response.raise_for_status()

        return response.json()
    
    def get_tag_detail(self, tag_id):
        url = f'{self.base_url}/tags/{tag_id}'

        response = self.client.get(url, headers=self.headers)
        response.raise_for_status()

        return response.json()
    
    def update_tag(self, tag_id, tag_name):
        url = f'{self.base_url}/tags/{tag_id}'
        payload = {
            "name": tag_name
        }

        response = self.client.put(url, headers=self.headers, json=payload)
        response.raise_for_status()

        return response.json()
    
    def delete_tag(self, tag_id):
        url = f'{self.base_url}/tags/{tag_id}'

        response = self.client.delete(url, headers=self.headers)
        response.raise_for_status()

        return response.json()

class CommandHandler:
    def __init__(self, args):
        self.args = args
        self.service = TagsService(self.args.url, self.args.token)

    def run(self):
        if self.args.tags_command == Commands.LIST.value:            
            tags = self.service.get_all_tags()
            print_formatted(self.args.format, tags)

        elif self.args.tags_command == Commands.CREATE.value:
            new_tag = self.service.create_tag(self.args.name)
            print_formatted(self.args.format, new_tag)

        elif self.args.tags_command == Commands.DETAIL.value:
            tag_detail = self.service.get_tag_detail(self.args.tag_id)
            print_formatted(self.args.format, tag_detail)

        elif self.args.tags_command == Commands.UPDATE.value:
            updated_tag = self.service.update_tag(self.args.id, self.args.name)
            print_formatted(self.args.format, updated_tag)

        elif self.args.tags_command == Commands.DELETE.value:
            self.service.delete_tag(self.args.id)
