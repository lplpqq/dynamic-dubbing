import json
import librosa
import numpy as np
from pathlib import Path
from pydub import AudioSegment

from dubbing.config import settings
from dubbing.audio import detect_peaks_from_audio, stretch_audio_to_match
from dubbing.segments import create_segments_from_peaks, mark_anchors_with_timing
from dubbing.translation import translate_with_peak_alignment
from dubbing.tts import generate_full_tts
from dubbing.video import replace_audio_in_video


def main():
    settings.output_dir.mkdir(exist_ok=True)
    print(f"Saving files to: {settings.output_dir.absolute()}\n")

    transcription_english = "Patient build up at the edge of the area. Oh, lovely link up play sets him up and he goes for the top corner. What a fantastic finish."

    with open("transcription.json") as f:
        word_timings = json.load(f)

    original_duration = 7.81

    original_audio_path = Path("audio.wav")
    if original_audio_path.exists():
        original_peaks = detect_peaks_from_audio(original_audio_path)
    else:
        print(f"Original audio not found at {original_audio_path}")
        print("Using default peaks from librosa analysis")
        original_peaks = np.array([0.81269841, 3.2275737, 4.87619048, 6.10684807])
        print(f"Using peaks: {original_peaks}")

    print(f"\n")

    segments = create_segments_from_peaks(word_timings, original_peaks)

    marked_text, anchor_info = mark_anchors_with_timing(transcription_english, segments, word_timings)
    print(f"\nMarked text:\n{marked_text}\n")

    full_translation = translate_with_peak_alignment(
        transcription_english,
        marked_text,
        original_duration,
        anchor_info
    )

    if full_translation:
        print(f"\n{settings.target_language_name} translation:\n{full_translation}\n")
    else:
        print("Translation failed!")
        exit(1)

    full_audio = generate_full_tts(full_translation)

    full_audio = stretch_audio_to_match(full_audio, original_duration)

    print("\nExtracting segments and verifying peaks...")

    final_audio = AudioSegment.empty()

    for seg in segments:
        start_ms = int(seg['start'] * 1000)
        end_ms = int(seg['end'] * 1000)

        segment_audio = full_audio[start_ms:end_ms]
        segment_export_path = settings.output_dir / f"seg_{seg['segment_num']:02d}_audio.mp3"
        segment_audio.export(segment_export_path, format="mp3")

        seg_duration = len(segment_audio) / 1000.0

        if seg['target_peak'] is not None:
            y, sr = librosa.load(segment_export_path)
            rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=512)[0]

            peak_frame = np.argmax(rms)
            peak_offset_s = librosa.frames_to_time(peak_frame, sr=sr, hop_length=512)

            actual_peak_time = seg['start'] + peak_offset_s
            peak_error = abs(actual_peak_time - seg['target_peak'])

            status = "OK" if peak_error < 0.1 else "WARN"
            print(
                f"{status} Segment {seg['segment_num']}: Target peak {seg['target_peak']:.2f}s, Actual {actual_peak_time:.2f}s (error: {peak_error:.3f}s)")
        else:
            print(f"  Segment {seg['segment_num']}: {seg_duration:.2f}s")

        final_audio += segment_audio

    print("\nFinalizing...")

    final_path = settings.output_dir / f"00_dubbed_final_{settings.target_language_code}.mp3"
    final_audio.export(final_path, format="mp3")

    final_duration = len(final_audio) / 1000.0

    print(f"\nSuccess - Peak-aligned dubbing completed")
    print(f"Final dubbed audio: {final_duration:.2f}s (target: {original_duration:.2f}s)")
    print(f"All files saved to: {settings.output_dir.absolute()}")

    if abs(final_duration - original_duration) < 0.1:
        print("Duration matches perfectly!")
    else:
        print(f"Duration off by {abs(final_duration - original_duration):.2f}s")

    try:
        replace_audio_in_video(final_path)
    except Exception as e:
        print(f"Failed to replace audio in video: {e}")

if __name__ == "__main__":
    main()
