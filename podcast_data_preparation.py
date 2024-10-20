import json
import os
import requests

class PodcastDataJsonReader:
    def __init__(self, json_path):
        self.json_path = json_path

    def read_json(self):
        with open(self.json_path, 'r', encoding='utf-8') as f:
            return json.load(f)['result']


class PodcastDataPreparation:
    def __init__(self, json_path, output_dir, video_width, video_height, key_frame_path):
        self.url_data_list = PodcastDataJsonReader(json_path).read_json()
        self.output_dir = output_dir
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        self.video_width = video_width
        self.video_height = video_height
        self.key_frame_path = key_frame_path

    def get_basic_video_info(self):
        return {
            'height': self.video_height,
            'width': self.video_width,
            # 'bgm_path': 'D:\Study\AIAgent\AIEnglishLearning\static_materials\scott-buckley-reverie(chosic.com).mp3',
            'bgm_path': -1,
            'output_path': os.path.join(self.output_dir, 'output.mp4'),
            'audio_fadeout_duration': 2,
            'bgm_volume': 0.5,
            'clips': []
        }

    def prepare_data(self):
        video_info_config = self.get_basic_video_info()
        for item in self.url_data_list:
            clip_info = {
                'audio_path': self.download_audio(item['audio_url']),
                'key_frame_path': self.key_frame_path,
                'duration': -1,
                'transition_pause_time': 0.5,
                'audio_speed': 1.1
            }
            video_info_config['clips'].append(clip_info)
        return video_info_config

    def download_audio(self, url):
        output_dir = os.path.join(self.output_dir, 'downloaded_audios')
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        local_filename = os.path.join(output_dir, url.split('/')[-1])
        if os.path.exists(local_filename):
            print(f"File {local_filename} already exists")
            return local_filename
        
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            with open(local_filename, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        print(f"Downloaded {url} to {local_filename}")
        return local_filename

def test_PodcastDataJsonReader():
    reader = PodcastDataJsonReader('D:\Study\AIAgent\AIPodcast\output\podcast_data.json')
    data = reader.read_json()
    for item in data:
        print(item)

def test_PodcastDataPreparation():
    preparation = PodcastDataPreparation('D:\Study\AIAgent\AIPodcast\output\podcast_data.json', 'D:\Study\AIAgent\AIPodcast\output\\episode_test')
    print(preparation.prepare_data())

if __name__ == '__main__':
    # test_PodcastDataJsonReader()
    test_PodcastDataPreparation()
