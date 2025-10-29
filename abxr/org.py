#!/usr/bin/env python3
#
# Copyright (c) 2024-2025 ABXR Labs, Inc.
# Released under the MIT License. See LICENSE file for details.
#

from enum import Enum

from abxr.api_service import ApiService
from abxr.output import print_formatted

class Commands(Enum):
    INFO = "info"

class OrgService(ApiService):
    def __init__(self, base_url, token):
        super().__init__(base_url, token)

    def get_org_info(self):
        url = f'{self.base_url}/current-organization'

        response = self.client.get(url, headers=self.headers)
        response.raise_for_status()

        return response.json()
    

class CommandHandler:
    def __init__(self, args):
        self.args = args
        self.service = OrgService(self.args.url, self.args.token)

    def run(self):
        if self.args.org_command == Commands.INFO.value:            
            org_info = self.service.get_org_info()
            print_formatted(self.args.format, org_info)