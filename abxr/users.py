#!/usr/bin/env python3
#
# Copyright (c) 2024-2025 ABXR Labs, Inc.
# Released under the MIT License. See LICENSE file for details.
#

import requests
import yaml
import json

from enum import Enum

from abxr.api_service import ApiService
from abxr.formats import DataOutputFormats

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

        response = requests.get(url, headers=self.headers)
        response.raise_for_status()

        json = response.json()

        data = json['data']

        if json['links']:
            while json['links']['next']:
                response = requests.get(json['links']['next'], headers=self.headers)
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

        response = requests.post(url, headers=self.headers, json=payload)
        response.raise_for_status()

        return response.json()
    
    def get_user_detail(self, user_id):
        url = f'{self.base_url}/users/{user_id}'

        response = requests.get(url, headers=self.headers)
        response.raise_for_status()

        return response.json()
    
    def update_user(self, user_id, first_name, last_name):
        url = f'{self.base_url}/users/{user_id}'
        payload = {
            "firstName": first_name,
            "lastName": last_name
        }

        response = requests.put(url, headers=self.headers, json=payload)
        response.raise_for_status()

        return response.json()
    
    def delete_user(self, user_id):
        url = f'{self.base_url}/users/{user_id}'

        response = requests.delete(url, headers=self.headers)
        response.raise_for_status()

        return response.json()

class CommandHandler:
    def __init__(self, args):
        self.args = args
        self.service = UsersService(self.args.url, self.args.token)

    def run(self):
        if self.args.users_command == Commands.LIST.value:            
            users = self.service.get_all_users()

            if self.args.format == DataOutputFormats.JSON.value:
                print(json.dumps(users))
            elif self.args.format == DataOutputFormats.YAML.value:
                print(yaml.dump(users))
            else:
                print("Invalid output format.")

        elif self.args.users_command == Commands.CREATE.value:
            if not self.args.first_name or not self.args.last_name or not self.args.email or not self.args.org_role_id:
                print("First name, last name, email, and organization role ID are required for creating a user.")
                return

            new_user = self.service.create_user(self.args.first_name, self.args.last_name, self.args.email, self.args.org_role_id)

            if self.args.format == DataOutputFormats.JSON.value:
                print(json.dumps(new_user))
            elif self.args.format == DataOutputFormats.YAML.value:
                print(yaml.dump(new_user))
            else:
                print("Invalid output format.")

        elif self.args.users_command == Commands.DETAILS.value:
            if not self.args.id:
                print("User ID is required for fetching user details.")
                return

            user_detail = self.service.get_user_detail(self.args.id)

            if self.args.format == DataOutputFormats.JSON.value:
                print(json.dumps(user_detail))
            elif self.args.format == DataOutputFormats.YAML.value:
                print(yaml.dump(user_detail))
            else:
                print("Invalid output format.")

        elif self.args.users_command == Commands.UPDATE.value:
            if not self.args.id or not self.args.first_name or not self.args.last_name:
                print("User ID, first name, and last name are required for updating a user.")
                return

            updated_user = self.service.update_user(self.args.id, self.args.first_name, self.args.last_name)

            if self.args.format == DataOutputFormats.JSON.value:
                print(json.dumps(updated_user))
            elif self.args.format == DataOutputFormats.YAML.value:
                print(yaml.dump(updated_user))
            else:
                print("Invalid output format.")

        elif self.args.users_command == Commands.DELETE.value:
            if not self.args.id:
                print("User ID is required for deleting a user.")
                return

            deleted = self.service.delete_user(self.args.id)

            if self.args.format == DataOutputFormats.JSON.value:
                print(json.dumps(deleted))
            elif self.args.format == DataOutputFormats.YAML.value:
                print(yaml.dump(deleted))
            else:
                print("Invalid output format.")
