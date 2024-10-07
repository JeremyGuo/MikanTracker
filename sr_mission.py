import threading,cv2,torch,os
from moviepy.editor import VideoFileClip

from sr_encoders import encoders
import config
import sys
import time
import subprocess as sp

from log import log
from subprocess import DEVNULL
from typing import List
import numpy as np

sys.path.append('third_party/realCUGAN/Real-CUGAN')
from upcunet_v3 import RealWaifuUpScaler

def get_total_size(directory):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(directory):
        for filename in filenames:
            file_path = os.path.join(dirpath, filename)
            if os.path.isfile(file_path):
                total_size += os.path.getsize(file_path)
    return total_size

def has_subtitles(file_path):
    # 使用 ffprobe 获取文件的流信息
    command = [
        'ffprobe', '-v', 'error', '-print_format', 'json', '-show_streams',
        '-select_streams', 's', file_path
    ]
    import json
    try:
        result = sp.run(command, stdout=sp.PIPE, stderr=sp.PIPE, text=True)
        streams = json.loads(result.stdout).get('streams', [])
        if len(streams) > 0:
            return [stream["index"] for stream in streams]
        return []
    except sp.CalledProcessError as e:
        return []

class UpScalerMission:
    def __init__(self, num_thread: int, scale, model, tile, cache_mode, alpha, encoder : str, inp_file : str, out_file : str, batch_size : str = '1G'):
        if encoder not in encoders:
            raise ValueError(f"Invalid encoder {encoder}")
        self.num_thread = num_thread
        self.encoder = encoder
        self.cache_mode = cache_mode
        self.tile = tile
        self.alpha = alpha
        self.scale = scale
        self.model = model
        self.inp_file = inp_file
        self.out_file = out_file
        if batch_size[-1] not in ['M', 'G']:
            raise ValueError(f"Invalid batch_size {batch_size}")
        if batch_size[-1] == 'M':
            self.batch_size = int(batch_size[:-1]) * 1024 * 1024
        else:
            self.batch_size = int(batch_size[:-1]) * 1024 * 1024 * 1024
        self.total_frames = 0
        self.total_super_resolution_frame = 0
        self.total_super_resolution_time_ms = 0
        self.total_encoded_frame = 0
        self.total_encoded_time_ms = 0
        self.clip_list = []
    
    def encode_clip(self, ext, fps, w, h, number_frames : int):
        start_time = time.time()
        clip_path = config.sr_tmp_dir / f'{self.clip_number}{ext}'
        cmd = []

        encoder_params = encoders[self.encoder]
        for param in encoder_params:
            cmd.append(param)
            cmd.append(str(encoder_params[param]))
        
        cmd = ['ffmpeg', '-r', str(fps), '-f', 'image2', '-s', f'{w}x{h}', '-i',
               f'{self.clip_folder}/%d.png', '-c:v', self.encoder] + cmd + ['-pix_fmt', 'yuv420p', str(clip_path)]
        if sp.Popen(cmd, stdout=DEVNULL, stderr=DEVNULL, stdin=DEVNULL).wait() != 0:
            log(f"Failed to encode clip {self.inp_file}")
            raise ValueError("Failed to encode clip")

        self.total_encoded_frame += number_frames
        self.total_encoded_time_ms += (time.time() - start_time) * 1000

        os.system(f'rm -rf {self.clip_folder}')
        self.clip_number += 1
        self.clip_folder = config.sr_tmp_dir / str(self.clip_number)
        os.system(f'mkdir -p {self.clip_folder}')

        self.clip_list.append(str(clip_path))
    
    def start(self):
        log(f"Start super resolution {self.inp_file}")
        objVideoreader = VideoFileClip(filename=self.inp_file)
        w,h = objVideoreader.reader.size
        fps = objVideoreader.reader.fps
        self.total_frames = objVideoreader.reader.nframes
        if_audio = objVideoreader.audio

        # Clear Tmp Directory
        os.system(f'rm -rf {config.sr_tmp_dir}/*')
        os.system(f'mkdir -p {config.sr_tmp_dir}')

        import pathlib
        output_suffix = pathlib.Path(self.out_file).suffix
        if output_suffix not in ['.mp4', '.mkv']:
            log(f"suffix not in ['.mp4', '.mkv'], got {output_suffix}")
            raise ValueError(f"Output file must be .mp4 or .mkv, but got {output_suffix}")

        # Audio saving & Create Writer
        audio_path = None
        if if_audio:
            audio_path = str(config.sr_tmp_dir / 'audio.wav')
            objVideoreader.audio.write_audiofile(audio_path, logger=None)
            log(f"Audio saved to {audio_path}")
        self.clip_number = 0
        self.clip_folder = config.sr_tmp_dir / str(self.clip_number)

        frame_index = 0
        os.system(f'mkdir -p {self.clip_folder}')
        
        statistic_lock = threading.Lock()
        def super_resolution_thread(frames, findexes):
            for frame, findex in zip(frames, findexes):
                start_time = time.time()
                with torch.no_grad():
                    writable_frame = np.copy(frame)
                    super_frame = self.model(writable_frame, self.tile, self.cache_mode, self.alpha)
                end_time = time.time()
                super_frame_path = self.clip_folder / f'{findex}.png'
                super_frame = cv2.cvtColor(super_frame, cv2.COLOR_RGB2BGR)
                cv2.imwrite(str(super_frame_path), super_frame)

                with statistic_lock:
                    self.total_super_resolution_frame += 1
                    self.total_super_resolution_time_ms += (end_time - start_time) * 1000

        HALF_BATCH_COUNT = 32
        running_threads : List[threading.Thread] = []
        thread_frames = []
        thread_indexes = []
        BATCH_COUNT = HALF_BATCH_COUNT * self.num_thread
        for frame in objVideoreader.iter_frames():
            thread_frames.append(frame)
            thread_indexes.append(frame_index)
            frame_index += 1

            if len(thread_frames) == HALF_BATCH_COUNT:
                if len(running_threads) >= self.num_thread:
                    running_threads[0].join()
                    running_threads = running_threads[1:]
                thread = threading.Thread(target=super_resolution_thread, args=(thread_frames, thread_indexes))
                thread.start()
                running_threads.append(thread)
                thread_frames = []
                thread_indexes = []

            # when folder size > batch_size, start encoding
            if frame_index % BATCH_COUNT == 0:
                for thread in running_threads:
                    thread.join()
                running_threads = []
                clip_total_size = get_total_size(self.clip_folder)
                if clip_total_size > self.batch_size:
                    self.encode_clip(output_suffix, fps, w, h, frame_index)
                    frame_index = 0
                    clip_total_size = 0
        if frame_index > 0:
            if len(thread_frames) > 0:
                if len(running_threads) >= self.num_thread:
                    running_threads[0].join()
                    running_threads = running_threads[1:]
                thread = threading.Thread(target=super_resolution_thread, args=(thread_frames, thread_indexes))
                thread.start()
                running_threads.append(thread)
                thread_frames = []
                thread_indexes = []
            for thread in running_threads:
                thread.join()
            self.encode_clip(output_suffix, fps, w, h, frame_index)
        
        file_list_path = config.sr_tmp_dir / 'file_list.txt'
        with open(file_list_path, 'w') as f:
            for clip in self.clip_list:
                f.write(f"file '{clip}'\n")
        tmp_out_file = config.sr_tmp_dir / f'tmp_out{output_suffix}'
        cmd = ['ffmpeg', '-safe', '0', '-loglevel', 'error', '-f', 'concat', '-i', str(file_list_path)]
        if audio_path: cmd += ['-i', audio_path, '-c:a', 'aac']
        else: cmd += ['-c', 'copy']
        cmd.append(str(tmp_out_file))
        if sp.Popen(cmd, stdout=DEVNULL, stderr=DEVNULL, stdin=DEVNULL).wait() != 0:
            log(f"Failed to concat clips {self.inp_file}")
            raise ValueError("Failed to concat clips")

        # 判断是否存在字幕
        subtitles = has_subtitles(self.inp_file)
        if len(subtitles) > 0:
            subtitle_extract_cmds = ['ffmpeg', '-i', f'{tmp_out_file}']
            for index in subtitles:
                subtitle_extract_cmds += ['-map', f'0:s:{index}', f"{config.sr_tmp_dir}/subtitle_{index}.srt"]
            if sp.Popen(subtitle_extract_cmds, stdout=DEVNULL, stderr=DEVNULL, stdin=DEVNULL).wait() != 0:
                log(f"Failed to extract subtitles from {self.inp_file}")
                raise ValueError("Failed to extract subtitles")
            
            encode_subtitle_cmds = ['ffmpeg', '-i', f'{tmp_out_file}']
            for index in subtitles:
                encode_subtitle_cmds += ['-f', 'srt', '-i', f"{config.sr_tmp_dir}/subtitle_{index}.srt"]
            encode_subtitle_cmds += ['-c:v', 'copy', '-c:a', 'copy', '-c:s', 'mov_text', f'{self.out_file}']
            if sp.Popen(encode_subtitle_cmds, stdout=DEVNULL, stderr=DEVNULL, stdin=DEVNULL).wait() != 0:
                log(f"Failed to encode subtitles to {self.out_file}")
                raise ValueError("Failed to encode subtitles")
        os.system(f'mv "{tmp_out_file}" "{self.out_file}"')
    
    def getProgress(self):
        if not self.total_frames or self.total_frames == 0:
            return 0, 0
        progress_encoded = self.total_encoded_frame / self.total_frames
        progress_super_resolution = self.total_super_resolution_frame / self.total_frames
        return progress_encoded, progress_super_resolution

    def getSpeed(self):
        if self.total_encoded_time_ms == 0:
            return 0, 0
        speed_encoded = self.total_encoded_frame / self.total_encoded_time_ms * 1000
        speed_super_resolution = self.total_super_resolution_frame / self.total_super_resolution_time_ms * 1000
        return speed_encoded, speed_super_resolution
