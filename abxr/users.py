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
    DETAILS = "details"
    UPDATE = "update"
    DELETE = "delete"


class UsersService(ApiService):
    def __init__(self, base_url, token):
        super().__init__(base_url, token)

    def get_all_users(self):
        url = f'{self.base_url}/users?per_page=20'

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
    
    def create_user(self, first_name, last_name, email, org_role_id):
        url = f'{self.base_url}/users'
        payload = {
            "firstName": first_name,
            "lastName": last_name,
            "email": email,
            "organizationRoleId": org_role_id
        }

        response = self.client.post(url, headers=self.headers, json=payload)
        response.raise_for_status()

        return response.json()
    
    def get_user_detail(self, user_id):
        url = f'{self.base_url}/users/{user_id}'

        response = self.client.get(url, headers=self.headers)
        response.raise_for_status()

        return response.json()
    
    def update_user(self, user_id, first_name, last_name):
        url = f'{self.base_url}/users/{user_id}'
        payload = {
            "firstName": first_name,
            "lastName": last_name
        }

        response = self.client.put(url, headers=self.headers, json=payload)
        response.raise_for_status()

        return response.json()
    
    def delete_user(self, user_id):
        url = f'{self.base_url}/users/{user_id}'

        response = self.client.delete(url, headers=self.headers)
        response.raise_for_status()

        return response.json()

class CommandHandler:
    def __init__(self, args):
        self.args = args
        self.service = UsersService(self.args.url, self.args.token)

    def run(self):
        if self.args.users_command == Commands.LIST.value:            
            users = self.service.get_all_users()
            print_formatted(self.args.format, users)

        elif self.args.users_command == Commands.CREATE.value:
            new_user = self.service.create_user(self.args.first_name, self.args.last_name, self.args.email, self.args.org_role_id)
            print_formatted(self.args.format, new_user)

        elif self.args.users_command == Commands.DETAILS.value:            
            user_detail = self.service.get_user_detail(self.args.id)
            print_formatted(self.args.format, user_detail)

        elif self.args.users_command == Commands.UPDATE.value:            
            updated_user = self.service.update_user(self.args.id, self.args.first_name, self.args.last_name)
            print_formatted(self.args.format, updated_user)

        elif self.args.users_command == Commands.DELETE.value:
            self.service.delete_user(self.args.id)

