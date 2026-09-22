#
# Copyright (c) 2024-2025 ABXR Labs, Inc.
# Released under the MIT License. See LICENSE file for details.
#

import re
import requests
from requests.adapters import HTTPAdapter, Retry

API_VERSION = 'v3'

RETRY_TOTAL = 5
RETRY_BACKOFF_FACTOR = 1
RETRY_STATUS_CODES = frozenset({429, 502, 503, 504})
RETRY_METHODS = frozenset({'GET', 'POST', 'PUT', 'PATCH', 'DELETE'})


def _build_client():
    """A requests.Session that retries transient failures with exponential backoff.

    Covers every v3 API call and the presigned part PUTs to storage. A bundle
    upload makes thousands of requests, so a single 503 from a pod that is
    being rolled during a deploy must not abort the whole run.

    Retries exhaust to the last response rather than raising, so call sites
    keep their existing raise_for_status() error handling.
    """
    retry = Retry(
        total=RETRY_TOTAL,
        backoff_factor=RETRY_BACKOFF_FACTOR,
        status_forcelist=RETRY_STATUS_CODES,
        allowed_methods=RETRY_METHODS,
        raise_on_status=False,
        respect_retry_after_header=True,
    )
    adapter = HTTPAdapter(max_retries=retry)

    session = requests.Session()
    session.mount('https://', adapter)
    session.mount('http://', adapter)
    return session


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

        self.client = _build_client()

        if ".local" in self._raw_base_url:
            requests.packages.urllib3.disable_warnings(
                requests.packages.urllib3.exceptions.InsecureRequestWarning
            )
            self.client.verify = False

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
