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


class TokenService(ApiService):
    def get_token_info(self):
        """Fetch token metadata from /api/token-info.

        Constructs URL directly from _base_origin to avoid triggering
        _detect_version() recursion — this endpoint IS the version detection
        mechanism.
        """
        url = f'{self._base_origin}/api/token-info'
        response = self.client.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()


class CommandHandler:
    def __init__(self, args):
        self.args = args
        self.service = TokenService(self.args.url, self.args.token)

    def run(self):
        if self.args.token_command == Commands.INFO.value:
            info = self.service.get_token_info()
            print_formatted(self.args.format, info)
