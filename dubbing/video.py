import os
import subprocess
from pathlib import Path

from dubbing.config import settings


def replace_audio_in_video(dubbed_audio: Path) -> Path:
    print("\nVideo audio replacement tool started")

    input_video = settings.input_video
    output_video = settings.output_video

    if not input_video.exists():
        print(f"Error: {input_video} not found")
        raise FileNotFoundError(f"{input_video} not found")

    if not dubbed_audio.exists():
        print(f"Error: {dubbed_audio} not found")
        raise FileNotFoundError(f"{dubbed_audio} not found")

    print(f"\nInput video: {input_video.absolute()}")
    print(f"Dubbed audio: {dubbed_audio.absolute()}")

    print("\nGetting video duration...")
    cmd_duration = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1:noprint_wrappers=1",
        str(input_video),
    ]

    try:
        result = subprocess.run(cmd_duration, capture_output=True, text=True, check=True)
        video_duration = float(result.stdout.strip())
        print(f"Video duration: {video_duration:.2f}s")
    except subprocess.CalledProcessError as e:
        print(f"Error getting video duration: {e.stderr}")
        raise RuntimeError(f"Error getting video duration: {e.stderr}")

    print("\nGetting audio duration...")
    cmd_audio_duration = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1:noprint_wrappers=1",
        str(dubbed_audio),
    ]

    try:
        result = subprocess.run(
            cmd_audio_duration, capture_output=True, text=True, check=True
        )
        audio_duration = float(result.stdout.strip())
        print(f"Audio duration: {audio_duration:.2f}s")
    except subprocess.CalledProcessError as e:
        print(f"Error getting audio duration: {e.stderr}")
        raise RuntimeError(f"Error getting audio duration: {e.stderr}")

    print("\nMatching duration...")
    duration_diff = abs(video_duration - audio_duration)
    print(
        f"Duration difference: {duration_diff:.3f}s ({duration_diff / video_duration * 100:.2f}%)"
    )

    strategy = "direct"
    stretch_ratio = 1.0
    if duration_diff < 0.05:
        print("Durations match perfectly, no adjustment needed")
    elif audio_duration < video_duration:
        print(f"Audio is shorter by {video_duration - audio_duration:.3f}s")
        print("Strategy: Stretch audio to match video duration")
        strategy = "stretch_audio"
        stretch_ratio = video_duration / audio_duration
        print(f"Stretch ratio (atempo): {stretch_ratio:.4f}")
    else:
        print(f"Audio is longer by {audio_duration - video_duration:.3f}s")
        print("Strategy: Stretch video to match audio duration")
        strategy = "stretch_video"
        stretch_ratio = audio_duration / video_duration
        print(f"Video speed: {stretch_ratio:.4f}x")

    print("\nProcessing...")

    temp_stretched_audio = settings.output_dir / "temp_stretched_audio.mp3"
    temp_stretched_video = settings.output_dir / "temp_stretched_video.mp4"

    cmd_mux = []

    if strategy == "direct":
        print("Replacing audio directly (no stretching)...")
        cmd_mux = [
            "ffmpeg",
            "-i",
            str(input_video),
            "-i",
            str(dubbed_audio),
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-shortest",
            "-y",
            str(output_video),
        ]
    elif strategy == "stretch_audio":
        print(f"Stretching audio with atempo={stretch_ratio:.4f}...")

        cmd_stretch_audio = [
            "ffmpeg",
            "-i",
            str(dubbed_audio),
            "-filter:a",
            f"atempo={stretch_ratio:.4f}",
            "-y",
            str(temp_stretched_audio),
        ]

        try:
            subprocess.run(cmd_stretch_audio, capture_output=True, check=True)
            print("Audio stretched successfully")
        except subprocess.CalledProcessError as e:
            print(f"Error stretching audio: {e.stderr}")
            raise RuntimeError(f"Error stretching audio: {e.stderr}")

        print("Muxing video with stretched audio...")
        cmd_mux = [
            "ffmpeg",
            "-i",
            str(input_video),
            "-i",
            str(temp_stretched_audio),
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-shortest",
            "-y",
            str(output_video),
        ]
    elif strategy == "stretch_video":
        print(f"Stretching video to {stretch_ratio:.4f}x speed...")

        video_speed_factor = stretch_ratio

        # use setpts filter to change video presentation timestamps (speed up or slow down)
        # we have to re-encode the video (libx264) because we are changing the actual frames timing
        cmd_stretch_video = [
            "ffmpeg",
            "-i",
            str(input_video),
            "-filter:v",
            f"setpts=PTS/{video_speed_factor}",
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "23",
            "-y",
            str(temp_stretched_video),
        ]

        try:
            subprocess.run(cmd_stretch_video, capture_output=True, check=True)
            print("Video stretched successfully")
        except subprocess.CalledProcessError as e:
            print(f"Error stretching video: {e.stderr}")
            raise RuntimeError(f"Error stretching video: {e.stderr}")

        print("Muxing stretched video with audio...")
        cmd_mux = [
            "ffmpeg",
            "-i",
            str(temp_stretched_video),
            "-i",
            str(dubbed_audio),
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-shortest",
            "-y",
            str(output_video),
        ]

    try:
        print("Running ffmpeg (this may take a while)...")
        subprocess.run(cmd_mux, capture_output=True, text=True, check=True)
        print("Muxing complete")
    except subprocess.CalledProcessError as e:
        print(f"Error during muxing: {e.stderr}")
        raise RuntimeError(f"Error during muxing: {e.stderr}")

    print("\nVerifying output...")
    if output_video.exists():
        output_size = output_video.stat().st_size / (1024 * 1024)
        print(f"Output file created: {output_video.absolute()}")
        print(f"Size: {output_size:.2f} MB")

        cmd_verify = [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1:noprint_wrappers=1",
            str(output_video),
        ]

        try:
            result = subprocess.run(cmd_verify, capture_output=True, text=True, check=True)
            output_duration = float(result.stdout.strip())
            print(f"Duration: {output_duration:.2f}s")
        except:
            pass
    else:
        print(f"Output file not created")
        raise FileNotFoundError(f"Output file not created")

    print("\nCleaning up...")
    if strategy == "stretch_audio" and temp_stretched_audio.exists():
        os.remove(temp_stretched_audio)
        print("Removed temporary audio file")

    if strategy == "stretch_video" and temp_stretched_video.exists():
        os.remove(temp_stretched_video)
        print("Removed temporary video file")

    print("\nVideo replacement successful")
    print(f"Final video: {output_video.absolute()}")

    return output_video
