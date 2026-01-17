import asyncio
import datetime as dt
import logging
import time

from fastapi import APIRouter, Depends

from papercast.dependencies import get_arxiv_paper_service
from papercast.entities import ArxivPaper, ArxivPaperStatus
from papercast.services.arxiv_paper_service import ArxivPaperService
from papercast.services.audio_service import AudioService
from papercast.services.podcast_service import PodcastService
from papercast.services.scraping_service import DailyPaperScraper
from papercast.services.text_to_speach_service import TextToSpeechService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/internal/api/v1/workers",
    tags=["workers"],
    responses={404: {"description": "Not found"}},
)


def success_response(message: str, data: dict) -> dict:
    response = {"success": True, "message": message, "data": data}
    return response


# TODO: target_dateの形式を指定する
@router.post("/start_script_writing/{target_date}")
async def start_script_writing(
    target_date: str,
    arxiv_paper_service: ArxivPaperService = Depends(get_arxiv_paper_service),
):
    scraper = DailyPaperScraper(dt.datetime.strptime(target_date, "%Y-%m-%d"))

    logger.info(f"Scraping papers for date: {target_date}...")
    arxiv_ids = scraper.get_papers_with_arxiv_ids()
    logger.info(f"Found {len(arxiv_ids)} arXiv papers for date {target_date}")

    papers: list[ArxivPaper] = []
    for arxiv_id in arxiv_ids:
        arxiv_url = f"https://arxiv.org/abs/{arxiv_id}"

        logger.info(f"Processing arXiv paper: {arxiv_url}")
        paper = arxiv_paper_service.create_arxiv_paper(arxiv_url)
        logger.info(f"Successfully processed arXiv paper: {arxiv_url}")

        papers.append(paper)

    service = PodcastService(arxiv_paper_service)

    relevant_papers = []
    for paper in papers:
        paper = await service.run(paper)
        relevant_papers.append(paper)

    return success_response(
        message="Script writing processing completed successfully",
        data={
            "target_date": target_date,
            "listed_paper_count": len(arxiv_ids),
            "processed_paper_count": len(relevant_papers),
        },
    )


@router.post("/start_tts")
async def start_tts(
    target_date: str,
    arxiv_paper_service: ArxivPaperService = Depends(get_arxiv_paper_service),
):
    tts_service = TextToSpeechService(arxiv_paper_service)

    logger.info(f"Starting TTS. target_date: {target_date}")

    arxiv_papers = arxiv_paper_service.select_target_arxiv_papers(target_date)

    logger.info(f"Updating project status to start TTS. target_date: {target_date}")

    start_time = time.time()
    await asyncio.wait_for(
        tts_service.generate_audio(arxiv_papers),
        timeout=60 * 60,  # 60 minutes timeout
    )
    execution_time = time.time() - start_time

    logger.info(f"Updating project status to TTS completed. target_date: {target_date}")
    for arxiv_paper in arxiv_papers:
        arxiv_paper_service.update_status(arxiv_paper, ArxivPaperStatus.tts_completed)

    return success_response(
        message="TTS completed successfully",
        data={
            "target_date": target_date,
            "processed_paper_count": len(arxiv_papers),
            "execution_time_seconds": round(execution_time, 2),
        },
    )


@router.post("/start_creating_audio")
async def start_creating_audio(
    target_date: str,
    arxiv_paper_service: ArxivPaperService = Depends(get_arxiv_paper_service),
):
    audio_service = AudioService()

    logger.info(f"Starting audio creation. target_date: {target_date}")

    arxiv_papers = arxiv_paper_service.select_target_arxiv_papers(target_date)
    target_papers = [paper for paper in arxiv_papers if paper.status == ArxivPaperStatus.tts_completed]

    if not target_papers:
        logger.info(f"No papers with tts_completed status found. target_date: {target_date}")
        return success_response(
            message="No papers to process",
            data={
                "target_date": target_date,
                "processed_paper_count": 0,
            },
        )

    logger.info(f"Found {len(target_papers)} papers with tts_completed status. target_date: {target_date}")

    start_time = time.time()
    await asyncio.wait_for(
        audio_service.generate_audio(target_papers),
        timeout=60 * 60,  # 60 minutes timeout
    )
    execution_time = time.time() - start_time

    logger.info(f"Updating paper status to podcast_created. target_date: {target_date}")
    for arxiv_paper in target_papers:
        arxiv_paper_service.update_status(arxiv_paper, ArxivPaperStatus.podcast_created)

    return success_response(
        message="Audio creation completed successfully",
        data={
            "target_date": target_date,
            "processed_paper_count": len(target_papers),
            "execution_time_seconds": round(execution_time, 2),
        },
    )
