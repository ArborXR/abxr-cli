#
# Copyright (c) 2024-2025 ABXR Labs, Inc.
# Released under the MIT License. See LICENSE file for details.
#

import re
import requests

API_VERSION = 'v3'


class ApiService:
    def __init__(self, base_url, token):
        self._raw_base_url = base_url

        if re.search(r'/api/v2(/|$)', base_url):
            raise ValueError(
                f"ABXR_API_URL points at v2 ('{base_url}'), which is no longer supported. "
                f"Use the base origin (e.g. https://api.xrdm.app) or /api/v3."
            )

        # Strip any /api suffix and what follows — we only need the base origin.
        # Handles: /api/v3, /api/internal, /api, or bare origin.
        self._base_origin = re.sub(r'/api(?:/\S+)?/?$', '', base_url.rstrip('/'))

        self.headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

        if ".local" in self._raw_base_url:
            requests.packages.urllib3.disable_warnings(
                requests.packages.urllib3.exceptions.InsecureRequestWarning
            )

            old_request_method = requests.Session.request
            def new_request_method(self, *args, **kwargs):
                kwargs['verify'] = False
                return old_request_method(self, *args, **kwargs)

            requests.Session.request = new_request_method

        self.client = requests

    @property
    def base_url(self):
        return self._raw_base_url

    def _url(self, *segments):
        """Build a v3 API URL for a resource.

        Example: self._url('apps', 'uuid', 'versions')
                 -> 'https://api.xrdm.app/api/v3/apps/uuid/versions'
        """
        path = '/'.join(str(s).strip('/') for s in segments)
        return f'{self._base_origin}/api/{API_VERSION}/{path}'

    def _get_all_pages(self, url):
        """Fetch all pages of a paginated API resource and return flat list.

        Follows links.next until exhausted.
        """
        response = self.client.get(url, headers=self.headers)
        response.raise_for_status()
        json_data = response.json()
        data = json_data.get('data', [])

        while json_data.get('links', {}).get('next'):
            response = self.client.get(json_data['links']['next'], headers=self.headers)
            response.raise_for_status()
            json_data = response.json()
            data += json_data.get('data', [])

        return data

    def _parse_response(self, response):
        """Parse JSON response, returning None for empty bodies (204 No Content)."""
        return response.json() if response.content else None
