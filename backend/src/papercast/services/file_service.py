import pathlib
import wave

from pydub import AudioSegment

from papercast.infrastructure.gcs import GCSFileUploadable


def build_downloads_path(filename: str) -> pathlib.Path:
    return pathlib.Path(f"downloads/papers/{filename}")


def build_tts_audio_directory(filename: str) -> pathlib.Path:
    return pathlib.Path(f"downloads/tts_audio/{filename}")


def build_completed_audio_directory(filename: str) -> pathlib.Path:
    return pathlib.Path(f"downloads/completed_audio/{filename}")


def resolve_tts_audio_path(filename: str, index: int) -> pathlib.Path:
    script_dir = build_tts_audio_directory(filename)
    return script_dir / f"{index}.wav"


def resolve_audio_output_path(filename: str) -> pathlib.Path:
    audio_dir = build_completed_audio_directory(filename)
    return audio_dir / "output.wav"


class TTSFileService(GCSFileUploadable):
    @classmethod
    def read_from_path(cls, audio_path: pathlib.Path) -> AudioSegment:
        return AudioSegment.from_wav(audio_path)

    @classmethod
    def write(cls, filename: str, index: int, pcm_data: bytes) -> pathlib.Path:
        audio_dir = build_tts_audio_directory(filename)
        audio_dir.mkdir(parents=True, exist_ok=True)

        audio_path = resolve_tts_audio_path(filename, index)
        with wave.open(str(audio_path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(24000)
            wf.writeframes(pcm_data)

        return audio_path

    @classmethod
    def download_from_gcs(cls, filename: str, index: int) -> pathlib.Path:
        audio_dir = build_tts_audio_directory(filename)
        audio_dir.mkdir(parents=True, exist_ok=True)

        audio_path = resolve_tts_audio_path(filename, index)
        cls._download_from_gcs(audio_path)
        return audio_path

    @classmethod
    async def bulk_download_from_gcs(cls, filename: str, script_file_count: int) -> list[pathlib.Path]:
        audio_dir = build_tts_audio_directory(filename)
        audio_dir.mkdir(parents=True, exist_ok=True)

        audio_paths = [resolve_tts_audio_path(filename, index) for index in range(script_file_count)]
        await cls._bulk_download_from_gcs(audio_paths)
        return audio_paths


class CompletedAudioFileService(GCSFileUploadable):
    @classmethod
    def read(cls, filename: str) -> AudioSegment:
        output_path = resolve_audio_output_path(filename)
        return AudioSegment.from_wav(output_path)

    @classmethod
    def write(cls, filename: str, audio: AudioSegment) -> pathlib.Path:
        audio_dir = build_completed_audio_directory(filename)
        audio_dir.mkdir(parents=True, exist_ok=True)

        output_path = resolve_audio_output_path(filename)
        audio.export(output_path, format="wav", bitrate="192k")
        return output_path

    @classmethod
    def download_from_gcs(cls, filename: str) -> pathlib.Path:
        audio_dir = build_completed_audio_directory(filename)
        audio_dir.mkdir(parents=True, exist_ok=True)

        audio_path = resolve_audio_output_path(filename)
        cls._download_from_gcs(audio_path)
        return audio_path
