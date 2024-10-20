from moviepy.editor import AudioFileClip, ImageClip, concatenate_videoclips, concatenate_audioclips, CompositeAudioClip, VideoFileClip, CompositeVideoClip
from moviepy.audio.AudioClip import AudioArrayClip
import numpy as np
from moviepy.config import change_settings
from moviepy.video.fx.all import speedx
from PIL import Image
import os
from moviepy.editor import TextClip, CompositeVideoClip
from moviepy.video.tools.subtitles import SubtitlesClip
from moviepy.editor import ColorClip
import time

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
    subtitle_config: {
        font:
        fontsize:
        color:
        y_position: 0.9
    }
    clips: [
        dict{
            audio_path, # -1 for silence
            audio_speed,
            key_frame_path,
            frame_size: {
                width: 
                height: 
                unit: # if not specified, use the video size. If (-1, height), scale the image to the height, keep the width auto. If (width, -1), scale the image to the width, keep the height auto.
            },
            duration,
            transition_pause_time,
            subtitle_text,
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
        self.clips_config = config.get('clips', [])
        self.config = config
        # include audio_clip, image_clip, duration, subtitle_text
        self.clips_info_dicts = []

    def _create_final_audio(self):
        cur_start_time = 0
        for clip_config in self.clips_config:
            cur_clip_info_dict = {}
            cur_clip_info_dict['audio_clip'] = self.create_audio_clip(clip_config)
            cur_clip_info_dict['image_clip'] = self.create_image_clip(clip_config, cur_clip_info_dict['audio_clip'].duration)
            cur_clip_info_dict['duration'] = cur_clip_info_dict['audio_clip'].duration
            cur_clip_info_dict['subtitle_text'] = clip_config.get('subtitle_text', '')
            cur_clip_info_dict['start_time'] = cur_start_time
            cur_start_time += cur_clip_info_dict['duration']
            self.clips_info_dicts.append(cur_clip_info_dict)

        total_duration = sum(clip_info_dict['duration'] for clip_info_dict in self.clips_info_dicts)

        audio_clips = [cur_clip_info_dict['audio_clip'] for cur_clip_info_dict in self.clips_info_dicts]
        concatenated_audio = concatenate_audioclips(audio_clips)

        if self.bgm_path and self.bgm_path != -1:
            bgm_clip = AudioFileClip(self.bgm_path).volumex(self.bgm_volume)
            bgm_clip = bgm_clip.subclip(0, total_duration).audio_fadeout(self.audio_fadeout_duration)
            final_audio = CompositeAudioClip([concatenated_audio, bgm_clip])
        else:
            final_audio = concatenated_audio

        return final_audio
    
    def create_pure_audio(self):
        audio_clip = self._create_final_audio()
        audio_clip.write_audiofile(self.output_path, codec='mp3', fps=44100)

    def create(self):
        # check if the output_path is a pure audio file
        if self.output_path.lower().endswith(('.mp3', '.wav', '.m4a')):
            self.create_pure_audio()
        else:
            self.create_video_fast()

    def create_video_fast(self):
        '''This implementation could be two times faster than the create_video method'''
        cur_start_time = 0
        for clip_config in self.clips_config:
            cur_clip_info_dict = {}
            cur_clip_info_dict['audio_clip'] = self.create_audio_clip(clip_config)
            cur_clip_info_dict['image_clip'] = self.create_image_clip(clip_config, cur_clip_info_dict['audio_clip'].duration)
            cur_clip_info_dict['duration'] = cur_clip_info_dict['audio_clip'].duration
            cur_clip_info_dict['subtitle_text'] = clip_config.get('subtitle_text', '')
            cur_clip_info_dict['start_time'] = cur_start_time
            cur_start_time += cur_clip_info_dict['duration']
            self.clips_info_dicts.append(cur_clip_info_dict)

        total_duration = sum(clip_info_dict['duration'] for clip_info_dict in self.clips_info_dicts)

        audio_clips = [cur_clip_info_dict['audio_clip'] for cur_clip_info_dict in self.clips_info_dicts]
        concatenated_audio = concatenate_audioclips(audio_clips)

        if self.bgm_path and self.bgm_path != -1:
            bgm_clip = AudioFileClip(self.bgm_path).volumex(self.bgm_volume)
            bgm_clip = bgm_clip.subclip(0, total_duration).audio_fadeout(self.audio_fadeout_duration)
            final_audio = CompositeAudioClip([concatenated_audio, bgm_clip])
        else:
            final_audio = concatenated_audio

        if self.config.get('background_video_path'):
            background_clip = self.create_background(duration=total_duration)
        else:
            background_clip = ColorClip(size=(self.width, self.height), color=(255, 255, 255)).set_duration(total_duration)

        final_video = background_clip
        for clip_info_dict in self.clips_info_dicts:
            video_clip = clip_info_dict['image_clip']
            if video_clip is not None:
                video_clip = video_clip.set_start(clip_info_dict['start_time'])
                video_clip = video_clip.set_position(("center", "center")).resize(height=self.height)
                final_video = CompositeVideoClip([final_video, video_clip])
            
        final_video = final_video.set_audio(final_audio)

        if self.config.get('subtitle_config'):
            final_video = self.add_subtitle(final_video, self.clips_info_dicts, self.config.get('subtitle_config', {}))

        time_start = time.time()
        final_video.write_videofile(
            self.output_path,
            codec="h264_nvenc",
            audio_codec='aac',
            fps=24,
            threads=8,
            ffmpeg_params=[
                "-b:v", "5M",
                "-preset", "fast",
                "-rc", "vbr",
                "-gpu", "0"
            ]
        )

        time_end = time.time()
        print(f"Video created and saved to {self.output_path}, time used: {time_end - time_start:.2f} seconds")

    def create_video(self):
        # create an empty video clip with the size of the output video
        canvas_clip = ColorClip(size=(self.width, self.height), color=(255, 255, 255, 0)).set_duration(self.config.get('duration', 0))
        
        foreground_clips = [canvas_clip]
        clip_info_dicts = []
        for clip_config in self.clips_config:
            video_clip, clip_info_dict = self.create_clip(clip_config)
            video_clip = video_clip.set_position(("center", "center")).resize(height=self.height)
            foreground_clips.append(video_clip)
            clip_info_dicts.append(clip_info_dict)
        foreground_video = concatenate_videoclips(foreground_clips, method="compose")

        if self.config.get('background_video_path'):
            background_clip = self.create_background(duration=foreground_video.duration)
            final_video = CompositeVideoClip([background_clip, foreground_video])
        else:
            final_video = foreground_video

        if self.bgm_path and self.bgm_path != -1:
            final_video = self.add_bgm(final_video)

        if self.config.get('subtitle_config'):
            final_video = self.add_subtitle(final_video, clip_info_dicts, self.config.get('subtitle_config', {}))

        # Specify the fps when writing the video file
        # final_video.write_videofile(self.output_path, codec="h264_nvenc", audio_codec='aac', fps=24, ffmpeg_params=["-b:v", "5M"])
        time_start = time.time()
        final_video.write_videofile(
            self.output_path, 
            codec="h264_nvenc", 
            audio_codec='aac', 
            fps=24, 
            threads=8,  # Use multiple threads for video processing
            ffmpeg_params=[
                "-b:v", "5M",  # Adjust the bitrate as needed
                "-preset", "fast",  # Speed up encoding
                "-rc", "vbr",  # Variable bitrate control for better performance
                "-gpu", "0"  # Ensure the GPU is used if multiple are available
            ]
        )
        time_end = time.time()
        print(f"Video created and saved to {self.output_path}, time used: {time_end - time_start:.2f} seconds")

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
            # concatenate silence to the end of the audio clip
            silence_duration = int(transition_pause_time * 44100)
            silence_audio = np.zeros((silence_duration, 2)) # 2 is the number of channels
            silence_audio_clip = AudioArrayClip(silence_audio, fps=44100)
            audio_clip = concatenate_audioclips([audio_clip, silence_audio_clip])
        else:
            silence_duration = int((clip_config.get('duration', 0)+transition_pause_time) * 44100)
            silence_audio = np.zeros((silence_duration, 2))
            audio_clip = AudioArrayClip(silence_audio, fps=44100)

        return audio_clip
    
    def create_image_clip(self, clip_config, image_clip_duration):
        if not clip_config.get('key_frame_path') or clip_config['key_frame_path'] == -1:
            return None

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
        self.resize_image(clip_config['key_frame_path'], resized_image_path, (target_width, target_height), ensure_fit=True)
        print(f"Image resized and saved to {resized_image_path}")
        
        # Set the opacity of the image clip
        image_clip = ImageClip(resized_image_path).set_duration(image_clip_duration)

        # Apply fade-out effect to the video clip
        if clip_config.get('fadeout_duration'):
            fadeout_duration = clip_config.get('fadeout_duration')
            image_clip = image_clip.crossfadeout(fadeout_duration)
        
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
        if clip_config.get('key_frame_path') and clip_config['key_frame_path'] != -1:
            image_clip = self.create_image_clip(clip_config, clip_duration)
            video_clip = image_clip.set_audio(audio_clip)
        else:
            video_clip = ColorClip(size=(1, 1), color=(0, 0, 0, 0)).set_duration(clip_duration).set_audio(audio_clip).set_opacity(0)

        # # Apply fade-out effect to the video clip
        # if clip_config.get('fadeout_duration'):
        #     fadeout_duration = clip_config.get('fadeout_duration')
        #     video_clip = video_clip.crossfadeout(fadeout_duration)

        clip_info_dict = {
            'duration': clip_duration,
            'subtitle_text': clip_config.get('subtitle_text', '')
        }
        return video_clip, clip_info_dict

    def add_subtitle(self, video_clip, clip_info_dicts, subtitle_config):
        font_size = subtitle_config.get('fontsize', 50)
        font_color = subtitle_config.get('color', 'white')
        stroke_color = subtitle_config.get('stroke_color', None)
        stroke_width = subtitle_config.get('stroke_width', 0)
        background_color = subtitle_config.get('background_color', None)
        
        # Define a text generator function for the subtitles
        def subtitle_generator(txt):
            txt_clip = TextClip(txt, font='Microsoft-YaHei-Bold-&-Microsoft-YaHei-UI-Bold',
                                fontsize=font_size,
                                color=font_color,
                                stroke_color=stroke_color,
                                stroke_width=stroke_width,
                                bg_color=background_color)
            return txt_clip

        # Create a list of subtitles with start and end times from clip_info_dicts
        subs = []
        sub_start_time = 0
        for clip_info in clip_info_dicts:
            subs.append(((sub_start_time, sub_start_time + clip_info['duration']), clip_info['subtitle_text']))
            sub_start_time += clip_info['duration']

        # Create the SubtitlesClip
        subtitles = SubtitlesClip(subs, subtitle_generator)

        # Overlay the subtitles below the video
        subtitle_y_position = subtitle_config.get('y_position', 'bottom')
        # if subtitle_y_position is a float and <1, then it is a percentage of the video height
        if isinstance(subtitle_y_position, float) and 0 < subtitle_y_position < 1:
            subtitle_y_position = int(subtitle_y_position * self.height)
        video_with_subtitles = CompositeVideoClip([video_clip, subtitles.set_position(('center', subtitle_y_position))])

        return video_with_subtitles

    def create_background(self, duration):
        background_path = self.config['background_video_path']
        if background_path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
            with Image.open(background_path) as img:
                if img.width != self.width or img.height != self.height:
                    resized_background_path = os.path.join(self.output_dir, os.path.splitext(os.path.basename(background_path))[0] + '_resized' + os.path.splitext(background_path)[1])
                    self.resize_image(background_path, resized_background_path, (self.width, self.height))
                    background_clip = (
                        ImageClip(resized_background_path)
                        .set_duration(duration)
                    )
                else:
                    background_clip = (
                        ImageClip(background_path)
                        .set_duration(duration)
                    )
        else:
            background_clip = VideoFileClip(background_path)
            if background_clip.size != (self.width, self.height):
                background_clip = background_clip.resize((self.width, self.height))
            background_clip = background_clip.set_duration(duration)

        return background_clip

    def add_bgm(self, video_clip):
        bgm_clip = AudioFileClip(self.bgm_path).volumex(self.bgm_volume)
        bgm_clip = bgm_clip.subclip(0, video_clip.duration).audio_fadeout(self.audio_fadeout_duration)
        final_audio = CompositeAudioClip([video_clip.audio, bgm_clip])
        final_video = video_clip.set_audio(final_audio)
        return final_video

    @staticmethod
    def resize_image(input_path, output_path, target_size, ensure_fit=True):
        if os.path.exists(output_path):
            print(f"File {output_path} already exists")
            return
        with Image.open(input_path) as img:
            original_width, original_height = img.size
            target_width, target_height = target_size

            if ensure_fit:
                width_ratio = target_width / original_width
                height_ratio = target_height / original_height
                scale_factor = min(width_ratio, height_ratio)
            else:
                width_ratio = target_width / original_width
                height_ratio = target_height / original_height
                scale_factor = max(width_ratio, height_ratio)

            new_width = int(original_width * scale_factor)
            new_height = int(original_height * scale_factor)

            img = img.resize((new_width, new_height), Image.LANCZOS)
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

def test_create_video_fast():
    config = {
        'height': 1080,
        'width': 1920,
        'bgm_path': 'D:\Study\AIAgent\AIEnglishLearning\static_materials\scott-buckley-reverie(chosic.com).mp3',
        # 'background_video_path': 'D:\Study\AIAgent\AIPodcast\\assets\\raining_window_10min.mp4',
        'background_video_path': 'D:\Study\AIAgent\AIPodcast\\assets\\raining_window_img.jpg',
        'output_path': 'D:\Study\AIAgent\AIPodcast\output\output.mp4',
        'audio_fadeout_duration': 2,
        'bgm_volume': 0.5,
        'subtitle_config': {
            'y_position': 0.8,
            'background_color': 'black'
        },
        'clips': [
            {
                'audio_path': 'D:\Study\AIAgent\AIPodcast\output\episode_test\downloaded_audios\stretched_audios\\2b625210f2124f05808abf75c0fca9ee_stretched.mp3',
                'key_frame_path': 'D:\Study\AIAgent\AIPodcast\\assets\logo.png',
                'frame_size': {'width': -1, 'height': 508},
                'duration': -1,
                'transition_pause_time': 2,
                'audio_speed': 1.0,
                'subtitle_text': 'This is 是低调a test subtitle',
                'fadeout_duration': 2
            },
            {
                'audio_path': 'D:\Study\AIAgent\AIPodcast\output\episode_test\downloaded_audios\stretched_audios\\1b628e22456941de8392f891aa630d9a_stretched.mp3',
                # 'key_frame_path': 'D:\Study\AIAgent\AIEnglishLearning\output\cluster0\\1_key_frame_1.jpeg',
                'key_frame_path': -1,
                'frame_size': {'width': -1, 'height': 508},
                'duration': -1,
                'transition_pause_time': 1,
                'audio_speed': 1.0,
                'subtitle_text': 'This is 深度方a test subtitle'
            },
        ]
    }

    video_crafter = VideoCrafter(config)
    video_crafter.create()


def test_create_pure_audio():
    config = {
        'height': 1080,
        'width': 1920,
        'bgm_path': 'D:\Study\AIAgent\AIEnglishLearning\static_materials\scott-buckley-reverie(chosic.com).mp3',
        'output_path': 'D:\Study\AIAgent\AIPodcast\output\output.mp3',
        'audio_fadeout_duration': 2,
        'bgm_volume': 0.5,
        'clips': [
            {
                'audio_path': 'D:\Study\AIAgent\AIPodcast\output\episode_test\downloaded_audios\stretched_audios\\2b625210f2124f05808abf75c0fca9ee_stretched.mp3',
                'frame_size': {'width': -1, 'height': 508},
                'duration': -1,
                'transition_pause_time': 2,
                'audio_speed': 1.0,
                'subtitle_text': 'This is 是低调a test subtitle',
                'fadeout_duration': 2
            },
            {
                'audio_path': 'D:\Study\AIAgent\AIPodcast\output\episode_test\downloaded_audios\stretched_audios\\1b628e22456941de8392f891aa630d9a_stretched.mp3',
                'key_frame_path': -1,
                'frame_size': {'width': -1, 'height': 508},
                'duration': -1,
                'transition_pause_time': 1,
                'audio_speed': 1.0,
                'subtitle_text': 'This is 深度方a test subtitle'
            },
        ]
    }

    video_crafter = VideoCrafter(config)
    video_crafter.create()


def test_create_video():
    config = {
        'height': 1080,
        'width': 1920,
        'bgm_path': 'D:\Study\AIAgent\AIEnglishLearning\static_materials\scott-buckley-reverie(chosic.com).mp3',
        # 'background_video_path': 'D:\Study\AIAgent\AIPodcast\\assets\\raining_window_10min.mp4',
        'background_video_path': 'D:\Study\AIAgent\AIPodcast\\assets\\raining_window_img.jpg',
        'output_path': 'D:\Study\AIAgent\AIPodcast\output\output.mp4',
        'audio_fadeout_duration': 2,
        'bgm_volume': 0.5,
        'subtitle_config': {
            'y_position': 0.8,
            'background_color': 'black'
        },
        'clips': [
            {
                'audio_path': 'D:\Study\AIAgent\AIPodcast\output\episode_test\downloaded_audios\stretched_audios\\2b625210f2124f05808abf75c0fca9ee_stretched.mp3',
                'key_frame_path': 'D:\Study\AIAgent\AIPodcast\\assets\logo.png',
                'frame_size': {'width': -1, 'height': 508},
                'duration': -1,
                'transition_pause_time': 2,
                'audio_speed': 1.0,
                'subtitle_text': 'This is 是低调a test subtitle',
                'fadeout_duration': 2
            },
            {
                'audio_path': 'D:\Study\AIAgent\AIPodcast\output\episode_test\downloaded_audios\stretched_audios\\1b628e22456941de8392f891aa630d9a_stretched.mp3',
                # 'key_frame_path': 'D:\Study\AIAgent\AIEnglishLearning\output\cluster0\\1_key_frame_1.jpeg',
                'key_frame_path': -1,
                'frame_size': {'width': -1, 'height': 508},
                'duration': -1,
                'transition_pause_time': 1,
                'audio_speed': 1.0,
                'subtitle_text': 'This is 深度方a test subtitle'
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
    test_create_video_fast()

    # test_create_video()

    # test_create_pure_audio()

    # test_resize_image()

    # test_change_audio_speed_without_pitch()



