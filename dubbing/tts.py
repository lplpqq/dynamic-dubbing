from elevenlabs import VoiceSettings, ElevenLabs
from pydub import AudioSegment
from dubbing.config import settings

def generate_full_tts(translation: str) -> AudioSegment:
    print("Generating tts...")

    elevenlabs = ElevenLabs(api_key=settings.elevenlabs_api_key)

    voice_settings = VoiceSettings(
        stability=0.4,
        similarity_boost=0.75,
        style=1,
        use_speaker_boost=True
    )

    audio_bytes = elevenlabs.text_to_speech.convert(
        voice_id=settings.elevenlabs_voice_id,
        text=translation,
        model_id="eleven_multilingual_v2",
        voice_settings=voice_settings
    )
    # the api returns a generator, so we join the chunks
    all_bytes = b"".join(audio_bytes)

    full_tts_path = settings.output_dir / "00_full_tts_raw.mp3"
    with open(full_tts_path, 'wb') as f:
        f.write(all_bytes)

    full_audio = AudioSegment.from_file(full_tts_path, format="mp3")
    full_duration_s = len(full_audio) / 1000.0

    print(f"Generated full audio: {full_duration_s:.2f}s")
    
    return full_audio
