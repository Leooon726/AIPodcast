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
    def __init__(self, json_path, output_dir, video_width=1920, video_height=1080, key_frame_path=-1):
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
            'bgm_path': 'D:\Study\AIAgent\AIPodcast\\assets\lounge_jazz.mp3',
            'background_video_path': 'D:\Study\AIAgent\AIPodcast\\assets\\raining_window_10min.mp4',
            'output_path': os.path.join(self.output_dir, 'output.mp4'),
            'audio_fadeout_duration': 2,
            'bgm_volume': 0.3,
            'subtitle_config': {
                'y_position': 0.8,
                'background_color': 'black'
            },
            'clips': []
        }

    def prepare_data(self):
        video_info_config = self.get_basic_video_info()
        # Cover
        cover_clip_info = {
            'audio_path': -1,
            'key_frame_path': 'D:\Study\AIAgent\AIPodcast\\assets\cover.png',
            'frame_size': {'width': 1920, 'height': 1080, 'unit': 'pixel'},
            'duration': 1,
            'fadeout_duration': 0,
            'transition_pause_time': 0.0,
            'subtitle_text': ''
        }
        video_info_config['clips'].append(cover_clip_info)
        # Opening
        opening_clip_info = {
            'audio_path': -1,
            'key_frame_path': 'D:\Study\AIAgent\AIPodcast\\assets\logo.png',
            'frame_size': {'width': -1, 'height': 0.5, 'unit': 'ratio'},
            'duration': 3,
            'fadeout_duration': 2,
            'transition_pause_time': 0.3,
            'subtitle_text': ''
        }
        video_info_config['clips'].append(opening_clip_info)
        # Body
        for item in self.url_data_list:
            clip_info = {
                'audio_path': self.download_audio(item['audio_url']),
                'key_frame_path': self.key_frame_path,
                'duration': -1,
                'transition_pause_time': 0.3,
                'audio_speed': 1.1,
                'subtitle_text': self.get_subtitle(item['sentence'])
            }
            video_info_config['clips'].append(clip_info)
        return video_info_config

    def get_basic_pure_audio_info(self):
        return {
            'bgm_path': 'D:\Study\AIAgent\AIPodcast\\assets\lounge_jazz.mp3',
            'output_path': os.path.join(self.output_dir, 'output.mp3'),
            'audio_fadeout_duration': 2,
            'bgm_volume': 0.3,
            'clips': []
        }

    def prepare_pure_audio_data(self):
        pure_audio_info_config = self.get_basic_pure_audio_info()
        # Opening
        opening_clip_info = {
            'audio_path': -1,
            'duration': 2,
        }
        pure_audio_info_config['clips'].append(opening_clip_info)
        # Body
        for item in self.url_data_list:
            clip_info = {
                'audio_path': self.download_audio(item['audio_url']),
                'duration': -1,
                'transition_pause_time': 0.3,
                'audio_speed': 1.1,
            }
            pure_audio_info_config['clips'].append(clip_info)
        return pure_audio_info_config

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

    def get_subtitle(self, sentence):
        '''input: 原来如此。（恍然大悟）啊，我懂了。
        output: 原来如此。啊，我懂了。
        sometimes there is no '（' or '）' in the sentence, so we need to handle this situation
        '''
        while '（' in sentence and '）' in sentence:
            start = sentence.index('（')
            end = sentence.index('）') + 1
            sentence = sentence[:start] + sentence[end:]
        return sentence

def test_PodcastDataJsonReader():
    reader = PodcastDataJsonReader('D:\Study\AIAgent\AIPodcast\output\podcast_data.json')
    data = reader.read_json()
    for item in data:
        print(item)

def test_PodcastDataPreparation():
    preparation = PodcastDataPreparation('D:\Study\AIAgent\AIPodcast\output\episode_test\\test_long.json', 'D:\Study\AIAgent\AIPodcast\output\\episode_test')
    print(preparation.prepare_data())

def test_get_subtitle():
    preparation = PodcastDataPreparation('D:\Study\AIAgent\AIPodcast\output\episode_test\\test_long.json', 'D:\Study\AIAgent\AIPodcast\output\\episode_test')
    print(preparation.get_subtitle("原来（思考片刻）“我要做”，就是我们该做却总是拖延的事情，对吧？"))

if __name__ == '__main__':
    # test_PodcastDataJsonReader()
    # test_PodcastDataPreparation()
    test_get_subtitle()
