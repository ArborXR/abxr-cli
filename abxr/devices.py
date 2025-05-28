#!/usr/bin/env python3
#
# Copyright (c) 2024-2025 ABXR Labs, Inc.
# Released under the MIT License. See LICENSE file for details.
#

import requests
import yaml
import json
from tqdm import tqdm

from enum import Enum

from abxr.api_service import ApiService
from abxr.multipart import MultipartFileS3
from abxr.formats import DataOutputFormats

class Commands(Enum):
    LIST = "list"
    DETAILS = "details"
    LAUNCH_APP = "launch"
    REBOOT = "reboot"

class DevicesService(ApiService):
    def __init__(self, base_url, token):
        super().__init__(base_url, token)
        
    def get_all_devices(self):
        url = f'{self.base_url}/devices?per_page=20'

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
    
    def get_device_detail(self, device_id):
        url = f'{self.base_url}/devices/{device_id}'

        response = requests.get(url, headers=self.headers)
        response.raise_for_status()

        return response.json()
    
    def launch_app(self, device_id, app_id):
        url = f'{self.base_url}/devices/{device_id}/launch/{app_id}'

        response = requests.post(url, headers=self.headers)
        response.raise_for_status()

        return response.json()
    
    def reboot_device(self, device_id):
        url = f'{self.base_url}/devices/{device_id}/reboot'
        
        response = requests.post(url, headers=self.headers)
        response.raise_for_status()
        
        return response.json()



class CommandHandler:
    def __init__(self, args):
        self.args = args
        self.service = DevicesService(self.args.url, self.args.token)

    def run(self):
        if self.args.apps_command == Commands.LIST.value:            
            devices_list = self.service.get_all_devices()

            if self.args.format == DataOutputFormats.JSON.value:
                print(json.dumps(devices_list))
            elif self.args.format == DataOutputFormats.YAML.value:
                print(yaml.dump(devices_list))
            else:
                print("Invalid output format.")

        elif self.args.apps_command == Commands.DETAILS.value:
            device_detail = self.service.get_device_detail(self.args.device_id)

            if self.args.format == DataOutputFormats.JSON.value:
                print(json.dumps(device_detail))
            elif self.args.format == DataOutputFormats.YAML.value:
                print(yaml.dump(device_detail))
            else:
                print("Invalid output format.")

        elif self.args.apps_command == Commands.LAUNCH_APP.value:
            self.service.launch_app(self.args.device_id, self.args.app_id)

        elif self.args.apps_command == Commands.REBOOT.value:
            self.service.reboot_device(self.args.device_id)

