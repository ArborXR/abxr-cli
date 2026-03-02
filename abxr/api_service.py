#
# Copyright (c) 2024-2025 ABXR Labs, Inc.
# Released under the MIT License. See LICENSE file for details.
#

import re
import sys
import requests

class ApiService:
    def __init__(self, base_url, token, _api_version=None):
        self._raw_base_url = base_url
        self._base_origin = re.sub(r'/api/v\d+/?$', '', base_url.rstrip('/'))
        self._api_version = _api_version
        self._version_detected = _api_version is not None

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

    def _detect_version(self):
        """Lazily detect API version from /api/token-info endpoint.

        Called once on first _url() invocation and caches result.
        Raises on failure — no silent fallback to v2.
        """
        if self._version_detected:
            return

        url = f'{self._base_origin}/api/token-info'
        response = self.client.get(url, headers=self.headers)
        response.raise_for_status()

        data = response.json().get('data', response.json())
        detected = data['api_version']

        # Check if raw base URL has a baked-in version that differs from detected
        raw_match = re.search(r'/api/(v\d+)/?$', self._raw_base_url)
        if raw_match:
            raw_version = raw_match.group(1)
            if raw_version != detected:
                print(
                    f"Warning: ABXR_API_URL contains version '{raw_version}' but token is '{detected}'. "
                    f"Using detected version '{detected}'.",
                    file=sys.stderr
                )

        self._api_version = detected
        self._version_detected = True

    def _url(self, *segments):
        """Build a version-aware URL for an API resource.

        Triggers lazy version detection on first call, then uses cached version.

        Example: self._url('apps', 'uuid', 'versions')
                 -> 'https://api.xrdm.app/api/v2/apps/uuid/versions'
        """
        self._detect_version()
        path = '/'.join(str(s).strip('/') for s in segments)
        return f'{self._base_origin}/api/{self._api_version}/{path}'

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

    @staticmethod
    def _normalize_status(raw_status):
        """Normalize API status to canonical uppercase form.
        v2 returns enum names (AVAILABLE, ERROR); v3 returns values (available, error).
        """
        if not raw_status:
            return raw_status
        return raw_status.upper()

    @staticmethod
    def _get_hash(data, field='sha512'):
        """Extract hash from v2 flat field or v3 nested checksum object."""
        checksum = data.get('checksum')
        if isinstance(checksum, dict):
            value = checksum.get('value')
            if value:
                return value
        return data.get(field)
