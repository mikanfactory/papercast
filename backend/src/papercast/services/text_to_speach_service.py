import asyncio
import logging
from logging import getLogger

from google import genai
from google.genai import types
from google.genai.errors import ServerError
from langchain.text_splitter import CharacterTextSplitter
from tenacity import before_sleep_log, retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from papercast.config import GEMINI_API_KEY
from papercast.entities import ArxivPaper, ArxivPaperStatus
from papercast.services.arxiv_paper_service import ArxivPaperService
from papercast.services.file_service import TTSFileService

logger = getLogger(__name__)
GEMINI_MODEL = "gemini-2.5-flash-preview-tts"


class TextToSpeechService:
    def __init__(self, arxiv_paper_service: ArxivPaperService):
        self.client = genai.Client(api_key=GEMINI_API_KEY)
        self.semaphore = asyncio.Semaphore(3)
        self.arxiv_paper_service = arxiv_paper_service

    @staticmethod
    def split_script(source_script: str) -> list[str]:
        text_splitter = CharacterTextSplitter.from_tiktoken_encoder(
            separator="\n",
            chunk_size=4000,  # 長過ぎると途中で途切れる
            chunk_overlap=0,
        )
        chunks = text_splitter.split_text(source_script)
        return chunks

    async def _invoke(self, script: str) -> bytes:
        response = await self.client.aio.models.generate_content(
            model=GEMINI_MODEL,
            contents=script,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    multi_speaker_voice_config=types.MultiSpeakerVoiceConfig(
                        speaker_voice_configs=[
                            types.SpeakerVoiceConfig(
                                speaker="Speaker1",
                                voice_config=types.VoiceConfig(
                                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                        voice_name="Alnilam",
                                    )
                                ),
                            ),
                            types.SpeakerVoiceConfig(
                                speaker="Speaker2",
                                voice_config=types.VoiceConfig(
                                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                        voice_name="Autonoe",
                                    )
                                ),
                            ),
                        ]
                    )
                ),
            ),
        )

        # AttributeErrorが発生することがあるため、_generateメソッドで再試行する
        data = response.candidates[0].content.parts[0].inline_data.data
        return data

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((ServerError, AttributeError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    async def _generate(self, arxiv_paper: ArxivPaper, script: str, index: int) -> None:
        async with self.semaphore:
            logger.info(f"Generating audio for arxiv paper: {str(arxiv_paper)}, index: {index}")
            data = await self._invoke(script)

        logger.info(f"Saving audio for arxiv paper {arxiv_paper}, index {index}.")
        source_file_path = TTSFileService.write(arxiv_paper.paper_id, index, data)
        TTSFileService.upload_gcs_from_file(source_file_path)

    async def _generate_arxiv_paper_audio(self, arxiv_paper: ArxivPaper) -> None:
        chunked_scripts = self.split_script(arxiv_paper.script)
        logger.info(f"Splitting script for {arxiv_paper} into {len(chunked_scripts)} chunks.")

        tasks = []
        for i, script in enumerate(chunked_scripts):
            tasks.append(self._generate(arxiv_paper, script, i))

        await asyncio.gather(*tasks)

        arxiv_paper.status = ArxivPaperStatus.tts_completed
        arxiv_paper.script_file_count = len(chunked_scripts)
        self.arxiv_paper_service.update(arxiv_paper)
        logger.info(
            f"Updated arxiv_paper {arxiv_paper} status to tts_completed with {len(chunked_scripts)} audio files"
        )

    async def _generate_audio(self, arxiv_papers: list[ArxivPaper]) -> None:
        for arxiv_paper in arxiv_papers:
            if arxiv_paper.status == ArxivPaperStatus.script_created:
                await self._generate_arxiv_paper_audio(arxiv_paper)
            else:
                logger.info(f"Skipping audio generation for paper (already completed): {str(arxiv_paper)}")

    async def generate_audio(self, arxiv_papers: list[ArxivPaper]) -> None:
        logger.info("Starting audio generation for chapters.")
        await self._generate_audio(arxiv_papers)
        logger.info("Audio generation completed successfully.")
