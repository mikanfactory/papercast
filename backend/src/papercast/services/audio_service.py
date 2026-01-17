import gc
import pathlib
from logging import getLogger

from pydub import AudioSegment
from pydub.silence import detect_nonsilent

from papercast.entities import ArxivPaper
from papercast.services.file_service import CompletedAudioFileService, TTSFileService

logger = getLogger(__name__)


def normalize(audio: AudioSegment, target_dBFS=-16.0):
    change_in_dBFS = target_dBFS - audio.dBFS
    return audio.apply_gain(change_in_dBFS)


def trim_silence(audio: AudioSegment, silence_thresh=-40, min_silence_len=500):
    nonsilent_ranges = detect_nonsilent(audio, min_silence_len=min_silence_len, silence_thresh=silence_thresh)
    if not nonsilent_ranges:
        return audio
    start_trim = nonsilent_ranges[0][0]
    end_trim = nonsilent_ranges[-1][1]
    return audio[start_trim:end_trim]


class AudioService:
    def __init__(self, audio_resource_directory: str = "resources"):
        self.audio_resource_directory = pathlib.Path(audio_resource_directory)
        self.jingle_path = self.audio_resource_directory / "jingle.mp3"
        self.opening_call_path = self.audio_resource_directory / "opening_call.wav"
        self.bgm_path = self.audio_resource_directory / "bgm.mp3"

    def _coordinate_jingle(self) -> AudioSegment | None:
        if not self.jingle_path.exists() or not self.opening_call_path.exists():
            logger.warning("Jingle or opening call resource files not found. Skipping jingle.")
            return None

        jingle_audio = AudioSegment.from_mp3(self.jingle_path)
        jingle_audio = normalize(jingle_audio)
        jingle_audio = trim_silence(jingle_audio)

        opening_call = AudioSegment.from_wav(self.opening_call_path)
        opening_call = normalize(opening_call)
        opening_call = trim_silence(opening_call)

        opening = jingle_audio.overlay(opening_call, position=8000)

        return opening

    @staticmethod
    async def _coordinate_script(arxiv_paper: ArxivPaper) -> AudioSegment:
        logger.info(f"Downloading TTS file for paper {arxiv_paper.paper_id}")
        file_paths = await TTSFileService.bulk_download_from_gcs(arxiv_paper.paper_id, arxiv_paper.script_file_count)

        acc = AudioSegment.empty()
        for file_path in file_paths:
            script_audio = TTSFileService.read_from_path(file_path)

            script_audio = normalize(script_audio)
            script_audio = trim_silence(script_audio)
            acc += script_audio

            del script_audio
            gc.collect()

        return acc

    def _coordinate_bgm(self, script_audio_size: int) -> AudioSegment | None:
        if not self.bgm_path.exists():
            logger.warning("BGM resource file not found. Skipping BGM.")
            return None

        bgm_audio = AudioSegment.from_mp3(self.bgm_path)
        bgm_looped = (bgm_audio * (script_audio_size // len(bgm_audio) + 1))[:script_audio_size]
        bgm_quiet = bgm_looped - 13
        return bgm_quiet

    async def generate_audio(self, arxiv_papers: list[ArxivPaper]) -> None:
        logger.info("Generating audio for papers")

        logger.info("Starting audio generation")
        jingle_audio = self._coordinate_jingle()

        for arxiv_paper in arxiv_papers:
            script_audio = await self._coordinate_script(arxiv_paper)

            bgm_audio = self._coordinate_bgm(len(script_audio))
            if bgm_audio is not None:
                script_audio = script_audio.overlay(bgm_audio)

            if jingle_audio is not None:
                output_audio = jingle_audio + script_audio
            else:
                output_audio = script_audio

            source_file_path = CompletedAudioFileService.write(arxiv_paper.paper_id, output_audio)
            CompletedAudioFileService.upload_gcs_from_file(source_file_path)

            del script_audio, output_audio
            if bgm_audio is not None:
                del bgm_audio
            gc.collect()

        logger.info("Audio generation completed successfully.")
