from moviepy.editor import AudioFileClip, ImageClip, concatenate_videoclips, concatenate_audioclips, CompositeAudioClip
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
    output_path: 
    audio_fadeout_duration: 
    bgm_volume:
    clips: [dict{audio_path, key_frame_path,duration,transition_pause_time,audio_speed}]
    audio_path = -1, then silence
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

    def create_video(self):
        video_clips = []
        for clip_config in self.clips:
            video_clips.append(self.create_video_clip(clip_config))
        final_video = concatenate_videoclips(video_clips)
        
        if self.bgm_path and self.bgm_path != -1:
            final_video = self.add_bgm(final_video)
        
        # Specify the fps when writing the video file
        final_video.write_videofile(self.output_path, codec='libx264', audio_codec='aac', fps=24)
        print(f"Video created and saved to {self.output_path}")

    def create_video_clip(self, clip_config):
        transition_pause_time = clip_config.get('transition_pause_time', 0)
        audio_speed = clip_config.get('audio_speed', 1.0)
        
        # create audio clip
        if clip_config['audio_path'] != -1:
            # Change audio speed without altering pitch
            if audio_speed != 1.0:
                modified_audio_path = change_audio_speed_without_pitch(clip_config['audio_path'], audio_speed, self.output_dir)
                audio_clip = AudioFileClip(modified_audio_path)
            else:
                audio_clip = AudioFileClip(clip_config['audio_path'])
            
            # Apply fade-in and fade-out to reduce noise
            audio_clip = audio_clip.audio_fadein(0.5).audio_fadeout(0.5)
        else:
            silence_duration = int(transition_pause_time * 44100)
            silence_audio = np.zeros((silence_duration, 2))
            audio_clip = AudioArrayClip(silence_audio, fps=44100)

        if 'duration' in clip_config and clip_config['duration'] > 0:
            clip_duration = clip_config['duration'] + transition_pause_time
        else:
            clip_duration = audio_clip.duration + transition_pause_time
        
        # resize image do not change the original image
        image_name = os.path.basename(clip_config['key_frame_path']).replace('.jpeg', '_resized.jpeg')
        resized_image_path = os.path.join(self.output_dir, image_name)
        self.resize_image(clip_config['key_frame_path'], resized_image_path, (self.width, self.height))
        print(f"Image resized and saved to {resized_image_path}")
        image_clip = ImageClip(resized_image_path).set_duration(clip_duration)
        
        # trim audio clip to match the video clip duration
        if clip_config['audio_path'] != -1:
            audio_clip = audio_clip.subclip(0, clip_duration - transition_pause_time)
        
        video_clip = image_clip.set_audio(audio_clip)
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
    if output_dir is None:
        output_path = audio_path.replace('.wav', '_stretched.wav')
    else:
        output_path = os.path.join(output_dir, os.path.basename(audio_path).replace('.wav', '_stretched.wav'))
    
    # Use ffmpeg to change audio speed without altering pitch
    command = f'ffmpeg -i "{audio_path}" -filter:a "atempo={speed_factor}" -vn "{output_path}"'
    os.system(command)
    
    return output_path

if __name__ == '__main__':
    config = {
        'height': 1920,
        'width': 1080,
        'bgm_path': 'D:\Study\AIAgent\AIEnglishLearning\static_materials\scott-buckley-reverie(chosic.com).mp3',
        'output_path': 'D:\Study\AIAgent\AIPodcast\output\output.mp4',
        'audio_fadeout_duration': 2,
        'bgm_volume': 0.5,
        'clips': [
            {
                'audio_path': 'D:\Study\AIAgent\AIEnglishLearning\output\cluster0\\1_output_audio.wav',
                'key_frame_path': 'D:\Study\AIAgent\AIEnglishLearning\output\cluster0\\1_key_frame_1.jpeg',
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

    # video_crafter.resize_image('D:\Study\AIAgent\AIEnglishLearning\static_materials\卡通女生图片.jpeg', 'D:\Study\AIAgent\AIPodcast\output\卡通女生图片_resized.jpeg', (1080, 1920))
