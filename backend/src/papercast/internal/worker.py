import datetime as dt
import logging

from fastapi import APIRouter, Depends

from papercast.dependencies import get_arxiv_paper_service
from papercast.entities import ArxivPaper
from papercast.services.arxiv_paper_service import ArxivPaperService
from papercast.services.podcast_service import PodcastService
from papercast.services.scraping_service import DailyPaperScraper

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/internal/api/v1/workers",
    tags=["workers"],
    responses={404: {"description": "Not found"}},
)


def success_response(message: str, data: dict) -> dict:
    response = {"success": True, "message": message, "data": data}
    return response


@router.post("/invoke/{target_date}")
async def invoke(
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
