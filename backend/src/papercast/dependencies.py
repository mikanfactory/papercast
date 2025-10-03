from papercast.repositories import ArxivPaperRepository
from papercast.services.arxiv_paper_service import ArxivPaperService
from papercast.services.db import supabase_client


def get_arxiv_paper_service() -> ArxivPaperService:
    arxiv_paper_repo = ArxivPaperRepository(supabase_client)
    return ArxivPaperService(arxiv_paper_repo)
