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

class AuditLogsService(ApiService):
    def __init__(self, base_url, token):
        super().__init__(base_url, token)

    def get_all_audit_logs(self, search, start_time, end_time):
        url = f'{self.base_url}/audit-logs?per_page=20'

        if search:
            url += f'&search={search}'
        if start_time:
            url += f'&start_time={start_time}'
        if end_time:
            url += f'&end_time={end_time}'

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

class CommandHandler:
    def __init__(self, args):
        self.args = args
        self.service = AuditLogsService(self.args.url, self.args.token)

    def run(self):
        if self.args.audit_logs_command == Commands.LIST.value:            
            audit_logs = self.service.get_all_audit_logs(self.args.search, self.args.start_time, self.args.end_time)
            print_formatted(self.args.format, audit_logs)