from papercast.services.markdown_parser import MarkdownParser
from papercast.services.scraping_service import DailyPaperScraper, ArxivPaperScraper, download_paper

def main():
    url = "https://arxiv.org/abs/2508.18106"
    paper_scraper = ArxivPaperScraper(url)
    info = paper_scraper.scrape_arxiv_info()
    destination = download_paper(info.paper_id)

    parser = MarkdownParser(pdf_path=str(destination))
    info.sections = parser.extract_sections_by_outline()

    print(info)


if __name__ == "__main__":
    main()
