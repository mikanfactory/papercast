from papercast.entities.arxiv_paper import ArxivPaper
from papercast.repositories.arxiv_paper_repository import ArxivPaperRepository
from papercast.services.markdown_parser import MarkdownParser
from papercast.services.scraping_service import ArxivPaperScraper, download_paper


class ArxivPaperService:
    def __init__(self, arxiv_paper_repo: ArxivPaperRepository):
        self.arxiv_paper_repo = arxiv_paper_repo

    def fetch_all_arxiv_papers(self) -> list[ArxivPaper]:
        return self.arxiv_paper_repo.select_all()

    def find_arxiv_paper(self, arxiv_paper_id: int) -> ArxivPaper:
        return self.arxiv_paper_repo.find(arxiv_paper_id)

    def create_arxiv_paper(self, url: str) -> ArxivPaper:
        paper_scraper = ArxivPaperScraper(url)
        arxiv_paper = paper_scraper.scrape_arxiv_info()
        destination = download_paper(arxiv_paper.paper_id)

        parser = MarkdownParser(pdf_path=str(destination))
        arxiv_paper.sections = parser.extract_all_sections_by_outline()

        return self.arxiv_paper_repo.create(arxiv_paper)

    def update(self, arxiv_paper: ArxivPaper) -> ArxivPaper:
        pass
