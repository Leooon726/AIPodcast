from moviepy.editor import AudioFileClip, ImageClip, concatenate_videoclips, concatenate_audioclips, CompositeAudioClip, VideoFileClip, CompositeVideoClip
from moviepy.audio.AudioClip import AudioArrayClip
import numpy as np
from moviepy.config import change_settings
from moviepy.video.fx.all import speedx
from PIL import Image
import os

# Specify the path to the ImageMagick binary
change_settings({"IMAGEMAGICK_BINARY": r"C:\Program Files\ImageMagick-7.1.1-Q16-HDRI\magick.exe"})

class VideoCrafter():
    '''
    This class uses config to create videos,
    a config is like:
    {
    height:
    width:
    bgm_path:
    background_video_path: # could be image or video or none
    output_path: 
    audio_fadeout_duration: 
    bgm_volume:
    clips: [
        dict{
            audio_path, # -1 for silence
            key_frame_path,
            frame_size: {
                width: 
                height: 
                unit: # if not specified, use the video size. If (-1, height), scale the image to the height, keep the width auto. If (width, -1), scale the image to the width, keep the height auto.
            },
            duration,
            transition_pause_time,
            audio_speed
        }
        ]
    }
    '''
    def __init__(self, config):
        self.height = config.get('height', 1080)
        self.width = config.get('width', 1920)
        self.bgm_path = config.get('bgm_path')
        self.output_path = config.get('output_path')
        self.output_dir = os.path.dirname(self.output_path)
        self.audio_fadeout_duration = config.get('audio_fadeout_duration')
        self.bgm_volume = config.get('bgm_volume')
        self.clips = config.get('clips', [])
        self.config = config

    def create_video(self):
        clips = []
        for clip_config in self.clips:
            clips.append(self.create_clip(clip_config))
        final_video = concatenate_videoclips(clips)
        
        if self.bgm_path and self.bgm_path != -1:
            final_video = self.add_bgm(final_video)
        
        if self.config.get('background_video_path'):
            final_video = self.add_background(final_video)

        # Specify the fps when writing the video file
        final_video.write_videofile(self.output_path, codec='libx264', audio_codec='aac', fps=24)
        print(f"Video created and saved to {self.output_path}")

    def create_audio_clip(self, clip_config):
        audio_speed = clip_config.get('audio_speed', 1.0)
        transition_pause_time = clip_config.get('transition_pause_time', 0)
        if clip_config['audio_path'] != -1:
            # Change audio speed without altering pitch
            if audio_speed != 1.0:
                modified_audio_path = change_audio_speed_without_pitch(clip_config['audio_path'], audio_speed)
                audio_clip = AudioFileClip(modified_audio_path)
            else:
                audio_clip = AudioFileClip(clip_config['audio_path'])
            
            # Apply fade-in and fade-out to reduce noise
            audio_clip = audio_clip.audio_fadein(0.5).audio_fadeout(0.5)
        else:
            silence_duration = int(transition_pause_time * 44100)
            silence_audio = np.zeros((silence_duration, 2))
            audio_clip = AudioArrayClip(silence_audio, fps=44100)

        return audio_clip
    
    def create_image_clip(self, clip_config, image_clip_duration):
        # Resize image according to frame_size
        frame_size = clip_config.get('frame_size', {'width': self.width, 'height': self.height})
        target_width = frame_size.get('width', self.width)
        target_height = frame_size.get('height', self.height)
        
        if target_width == -1 and target_height != -1:
            with Image.open(clip_config['key_frame_path']) as img:
                aspect_ratio = img.width / img.height
            target_width = int(target_height * aspect_ratio)
        elif target_height == -1 and target_width != -1:
            with Image.open(clip_config['key_frame_path']) as img:
                aspect_ratio = img.height / img.width
            target_height = int(target_width * aspect_ratio)
        elif target_width == -1 and target_height == -1:
            target_width = self.width
            target_height = self.height
        
        image_name, image_extension = os.path.splitext(os.path.basename(clip_config['key_frame_path']))
        resized_image_name = f"{image_name}_resized{image_extension}"
        resized_image_path = os.path.join(self.output_dir, resized_image_name)
        self.resize_image(clip_config['key_frame_path'], resized_image_path, (target_width, target_height))
        print(f"Image resized and saved to {resized_image_path}")
        image_clip = ImageClip(resized_image_path).set_duration(image_clip_duration)
        return image_clip
    
    def create_clip(self, clip_config):
        # create audio clip
        audio_clip = self.create_audio_clip(clip_config)

        transition_pause_time = clip_config.get('transition_pause_time', 0)
        if 'duration' in clip_config and clip_config['duration'] > 0:
            clip_duration = clip_config['duration'] + transition_pause_time
        else:
            clip_duration = audio_clip.duration + transition_pause_time

        # trim audio clip to match the video clip duration
        if clip_config['audio_path'] != -1:
            audio_clip = audio_clip.subclip(0, clip_duration - transition_pause_time)

        # create image clip
        image_clip = self.create_image_clip(clip_config, clip_duration)
        
        video_clip = image_clip.set_audio(audio_clip)
        return video_clip

    def add_background(self, video_clip):
        background_path = self.config['background_video_path']
        if background_path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
            with Image.open(background_path) as img:
                if img.width != self.width or img.height != self.height:
                    resized_background_path = os.path.join(self.output_dir, os.path.splitext(os.path.basename(background_path))[0] + '_resized' + os.path.splitext(background_path)[1])
                    self.resize_image(background_path, resized_background_path, (self.width, self.height))
                    background_clip = (
                        ImageClip(resized_background_path)
                        .set_duration(video_clip.duration)
                    )
                else:
                    background_clip = (
                        ImageClip(background_path)
                        .set_duration(video_clip.duration)
                    )
        else:
            background_clip = VideoFileClip(background_path)
            if background_clip.size != (self.width, self.height):
                background_clip = background_clip.resize((self.width, self.height))
            background_clip = background_clip.set_duration(video_clip.duration)
        video_clip = CompositeVideoClip([background_clip, video_clip.set_position("center")])
        return video_clip

    def add_bgm(self, video_clip):
        bgm_clip = AudioFileClip(self.bgm_path).volumex(self.bgm_volume)
        bgm_clip = bgm_clip.subclip(0, video_clip.duration).audio_fadeout(self.audio_fadeout_duration)
        final_audio = CompositeAudioClip([video_clip.audio, bgm_clip])
        final_video = video_clip.set_audio(final_audio)
        return final_video

    @staticmethod
    def resize_image(input_path, output_path, target_size):
        if os.path.exists(output_path):
            print(f"File {output_path} already exists")
            return
        with Image.open(input_path) as img:
            img = img.resize(target_size, Image.LANCZOS)  # Resize the image to the target size
            img.save(output_path)


def change_audio_speed_without_pitch(audio_path, speed_factor, output_dir=None):
    file_extension = os.path.splitext(audio_path)[1]
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(audio_path), 'stretched_audios')
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    output_path = os.path.join(output_dir, os.path.basename(audio_path).replace(file_extension, f'_stretched{file_extension}'))
    if os.path.exists(output_path):
        print(f"File {output_path} already exists")
        return output_path

    # Use ffmpeg to change audio speed without altering pitch
    command = f'ffmpeg -i "{audio_path}" -filter:a "atempo={speed_factor}" -vn "{output_path}"'
    os.system(command)
    
    return output_path

def test_main():
    config = {
        'height': 1920,
        'width': 1080,
        'bgm_path': 'D:\Study\AIAgent\AIEnglishLearning\static_materials\scott-buckley-reverie(chosic.com).mp3',
        'background_video_path': 'D:\Study\AIAgent\AIPodcast\\assets\\raining_window_10min.mp4',
        'output_path': 'D:\Study\AIAgent\AIPodcast\output\output.mp4',
        'audio_fadeout_duration': 2,
        'bgm_volume': 0.5,
        'clips': [
            {
                'audio_path': 'D:\Study\AIAgent\AIEnglishLearning\output\cluster0\\1_output_audio.wav',
                'key_frame_path': 'D:\Study\AIAgent\AIEnglishLearning\output\cluster0\\1_key_frame_1.jpeg',
                'frame_size': {'width': -1, 'height': 508},
                'duration': -1,
                'transition_pause_time': 1,
                'audio_speed': 1.2
            },
            {
                'audio_path': 'D:\Study\AIAgent\AIEnglishLearning\output\cluster0\\0_output_audio.wav',
                'key_frame_path': 'D:\Study\AIAgent\AIEnglishLearning\static_materials\卡通女生图片.jpeg',
                'duration': -1,
                'transition_pause_time': 2,
                'audio_speed': 1.0
            },
        ]
    }

    video_crafter = VideoCrafter(config)
    video_crafter.create_video()

def test_resize_image():
    VideoCrafter.resize_image('D:\Study\AIAgent\AIEnglishLearning\static_materials\卡通女生图片.jpeg', 'D:\Study\AIAgent\AIPodcast\output\卡通女生图片_resized.jpeg', (1080, 1920))

def test_change_audio_speed_without_pitch():
    change_audio_speed_without_pitch('D:\Study\AIAgent\AIPodcast\output\\test_input.mp3', 1.2, 'D:\Study\AIAgent\AIPodcast\output')

if __name__ == '__main__':
    test_main()

    # test_resize_image()

    # test_change_audio_speed_without_pitch()
