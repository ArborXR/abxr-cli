#
# Copyright (c) 2024-2025 ABXR Labs, Inc.
# Released under the MIT License. See LICENSE file for details.
#

import requests

class ApiService:
    def __init__(self, base_url, token):
        self.base_url = base_url
        self.headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

        if ".local" in self.base_url:
            requests.packages.urllib3.disable_warnings(
                requests.packages.urllib3.exceptions.InsecureRequestWarning
            )

            old_request_method = requests.Session.request
            def new_request_method(self, *args, **kwargs):
                kwargs['verify'] = False
                return old_request_method(self, *args, **kwargs)

            requests.Session.request = new_request_method

        self.client = requests

