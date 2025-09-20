from papercast.repositories.arxiv_paper_repository import ArxivPaperRepository
from papercast.services.arxiv_paper_service import ArxivPaperService
from papercast.services.db import supabase_client


def create_arxiv_paper():
    url = "https://arxiv.org/abs/2508.18106"
    service = ArxivPaperService(ArxivPaperRepository(supabase_client))
    arxiv_paper = service.create_arxiv_paper(url)
    print(arxiv_paper)


def find_arxiv_paper(id=1):
    service = ArxivPaperService(ArxivPaperRepository(supabase_client))
    arxiv_paper = service.find_arxiv_paper(id)
    print(arxiv_paper)


def main():
    find_arxiv_paper()


if __name__ == "__main__":
    main()
