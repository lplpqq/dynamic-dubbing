import subprocess
from pathlib import Path

import librosa
import numpy as np
from pydub import AudioSegment

from dubbing.config import settings


def detect_peaks_from_audio(audio_path: Path) -> np.ndarray:
    print("Detecting peaks from original audio...")
    print(f"Loading audio: {audio_path}")

    y, sr = librosa.load(audio_path)
    duration = librosa.get_duration(y=y, sr=sr)

    print(f"Duration: {duration:.2f}s")
    print(f"Sample rate: {sr} Hz")

    # find loud parts
    rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=512)[0]
    # normalize the volume levels to make peak finding more consistent
    rms_normalized = (rms - np.mean(rms)) / np.std(rms)

    peaks = librosa.util.peak_pick(
        rms_normalized,
        pre_max=15,
        post_max=15,
        pre_avg=40,
        post_avg=40,
        delta=0.5,
        wait=20,
    )

    peak_times = librosa.frames_to_time(peaks, sr=sr, hop_length=512)

    filtered_peaks = []
    for peak in peak_times:
        if peak < 0.3 or peak > duration - 0.3:
            continue
        if not filtered_peaks or (peak - filtered_peaks[-1]) > 0.4:
            filtered_peaks.append(peak)

    print(f"\nDetected {len(filtered_peaks)} peaks:")
    for i, peak in enumerate(filtered_peaks, 1):
        print(f"  Peak {i}: {peak:.3f}s")

    return np.array(filtered_peaks)


def stretch_audio_to_match(
    full_audio: AudioSegment, original_duration_target: float
) -> AudioSegment:
    print("\nStretching to match original duration...")

    full_duration_s = len(full_audio) / 1000.0

    print(f"Full audio: {full_duration_s:.2f}s")
    print(f"Target duration: {original_duration_target:.2f}s")

    global_stretch = full_duration_s / original_duration_target
    print(f"Stretch ratio: {global_stretch:.4f}")

    if abs(global_stretch - 1.0) > 0.01:
        print(f"Stretching with atempo={global_stretch:.4f}...")

        temp_input = settings.output_dir / "temp_full_input.mp3"
        temp_output = settings.output_dir / "temp_full_stretched.mp3"

        full_audio.export(temp_input, format="mp3")

        # cap the stretch ratio between 0.5x and 2.0x so it doesn't sound too weird
        clamped_stretch = max(0.5, min(2.0, global_stretch))
        # use the atempo filter to change audio speed without changing pitch
        cmd = [
            "ffmpeg",
            "-i",
            str(temp_input),
            "-filter:a",
            f"atempo={clamped_stretch}",
            "-y",
            str(temp_output),
        ]

        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
            full_audio = AudioSegment.from_file(temp_output)
            stretched_duration = len(full_audio) / 1000.0
            print(f"Stretched to {stretched_duration:.2f}s")
        except subprocess.CalledProcessError as e:
            print(f"Stretch failed: {e.stderr}")
    else:
        print("Duration matches, no stretch needed")

    return full_audio
