#!/usr/bin/env python3
#
# Copyright (c) 2024-2025 ABXR Labs, Inc.
# Released under the MIT License. See LICENSE file for details.
#

from tqdm import tqdm

from enum import Enum

from abxr.api_service import ApiService
from abxr.multipart import MultipartFileS3
from abxr.formats import DataOutputFormats
from abxr.output import print_formatted

class Commands(Enum):
    LIST = "list"
    DETAILS = "details"
    UPDATE = "update"
    UPLOAD = "upload"
    ATTACH_TAGS = "attach_tags"
    DETACH_TAGS = "detach_tags"
    
class VideosService(ApiService):
    MAX_PARTS_PER_REQUEST = 4

    def __init__(self, base_url, token):
        super().__init__(base_url, token)

    def _initiate_upload(self, file_name, video_type, video_mapping, video_display, video_packing, audio_encoding):
        url = f'{self.base_url}/videos'
        
        data = {
            'filename': file_name,
            'videoType': video_type,
            'videoMapping': video_mapping,
            'videoDisplay': video_display,
            'videoPacking': video_packing,
            'audioEncoding': audio_encoding
        }
        
        response = self.client.post(url, json=data, headers=self.headers)
        response.raise_for_status()
        
        return response.json()

    def _presigned_url(self, video_id, upload_id, key, part_numbers):
        url = f'{self.base_url}/videos/{video_id}/pre-sign'
        data = {
            'key': key, 
                'uploadId': upload_id, 
                'partNumbers': part_numbers 
                }
        
        response = self.client.post(url, json=data, headers=self.headers)
        response.raise_for_status()
        
        return response.json()

    def _complete_upload(self, video_id, upload_id, key, parts):
        url = f'{self.base_url}/videos/{video_id}/complete'
        data = {'key': key, 
                'uploadId': upload_id, 
                'parts': parts
                }
        
        response = self.client.post(url, json=data, headers=self.headers)
        response.raise_for_status()
        
        return response.json()

    def upload_video(self, file_path, video_type, video_mapping, video_display, video_packing, audio_encoding, silent):
        file = MultipartFileS3(file_path)

        response = self._initiate_upload(file.file_name, video_type, video_mapping, video_display, video_packing, audio_encoding)

        upload_id = response['uploadId']
        key = response['key']
        video_id = response['videoId']

        part_numbers = list(range(1, file.get_part_numbers() + 1))

        uploaded_parts = []

        with tqdm(total=file.get_size(), unit='B', unit_scale=True, desc=f'Uploading {file.file_name}', disable=silent) as pbar:
            for i in range(0, len(part_numbers), self.MAX_PARTS_PER_REQUEST):
                part_numbers_slice = part_numbers[i:i + self.MAX_PARTS_PER_REQUEST]
                
                presigned_url_response = self._presigned_url(video_id, upload_id, key, part_numbers_slice)
                
                for item in presigned_url_response:
                    part_number = item['partNumber']
                    presigned_url = item['presignedUrl']

                    part = file.get_part(part_number)
                    response = self.client.put(presigned_url, data=part)
                    response.raise_for_status()

                    uploaded_parts += [{'partNumber': part_number, 'eTag': response.headers['ETag']}]
                    pbar.update(len(part))
                
            complete_response = self._complete_upload(video_id, upload_id, key, uploaded_parts)
            return complete_response
        
    def get_all_videos(self):
        url = f'{self.base_url}/videos?per_page=20'

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
    
    def get_video_detail(self, video_id):
        url = f'{self.base_url}/videos/{video_id}'

        response = self.client.get(url, headers=self.headers)
        response.raise_for_status()

        return response.json()
    
    def update_video(self, video_id, name, description, video_type, video_mapping, video_display, video_package, audio_encoding, tags):
        url = f'{self.base_url}/videos/{video_id}'

        payload = {
            'name': name,
            'description': description,
            'videoType': video_type,
            'videoMapping': video_mapping,
            'videoDisplay': video_display,
            'videoPacking': video_package,
            'audioEncoding': audio_encoding,
            'tags': tags
        }

        response = self.client.put(url, headers=self.headers, json=payload)
        response.raise_for_status()

        return response.json()
    
    def add_tags_to_video(self, video_id, tags):
        url = f'{self.base_url}/videos/{video_id}/tags/attach'

        payload = {
            'tags': tags
        }

        response = self.client.patch(url, headers=self.headers, json=payload)
        response.raise_for_status()
        
        return response.json()

    def remove_tags_to_video(self, video_id, tags):
        url = f'{self.base_url}/videos/{video_id}/tags/detach'

        payload = {
            'tags': tags
        }

        response = self.client.patch(url, headers=self.headers, json=payload)
        response.raise_for_status()
        
        return response.json()
    

class CommandHandler:
    def __init__(self, args):
        self.args = args
        self.service = VideosService(self.args.url, self.args.token)

    def run(self):
        if self.args.videos_command == Commands.LIST.value:            
            videos_list = self.service.get_all_videos()
            print_formatted(self.args.format, videos_list)

        elif self.args.videos_command == Commands.DETAILS.value:
            video_detail = self.service.get_video_detail(self.args.video_id)
            print_formatted(self.args.format, video_detail)

        elif self.args.videos_commands == Commands.UPDATE.value:
            video_detail = self.service.update_video(self.args.video_id, self.args.name, self.args.description, self.args.video_type, self.args.video_mapping, self.args.video_display, self.args.video_packing, self.args.audio_encoding, self.args.tags)
            print_formatted(self.args.format, video_detail)

        elif self.args.videos_command == Commands.UPLOAD.value:
            video_version = self.service.upload_video(self.args.filename, self.args.video_type, self.args.video_mapping, self.args.video_display, self.args.video_packing, self.args.audio_encoding, self.args.silent)
            print_formatted(self.args.format, video_version)

        elif self.args.videos_command == Commands.ATTACH_TAGS.value:
            self.service.add_tags_to_video(self.args.video_id, self.args.tags)

        elif self.args.videos_command == Commands.DETACH_TAGS.value:
            self.service.remove_tags_to_video(self.args.video_id, self.args.tags)

