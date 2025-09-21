import datetime as dt
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from papercast.entities.arxiv_paper import ArxivPaper, download_path


class DailyPaperScraper:
    def __init__(self, target_date: dt.datetime):
        self.target_date = target_date

    def get_daily_papers_urls(self) -> list[str]:
        base = "https://huggingface.co/papers/date/"
        url = base + self.target_date.strftime("%Y-%m-%d")
        resp = requests.get(url)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        urls = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.startswith("/papers/") and len(href.split("/")) >= 3:
                full = "https://huggingface.co" + href
                if full not in urls:
                    urls.append(full)
        return urls

    def get_papers_with_arxiv_ids(self) -> set[str]:
        urls = self.get_daily_papers_urls()

        pattern = r"\b(\d{4}\.\d{5})\b"
        ids = set()
        for url in urls:
            match = re.search(pattern, url)
            if match:
                ids.add(match.group(1))

        return ids


class ArxivPaperScraper:
    def __init__(self, arxiv_url: str):
        self.arxiv_url = arxiv_url

    def scrape_arxiv_info(self) -> ArxivPaper:
        res = requests.get(self.arxiv_url)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")

        title = ""
        title_h1 = soup.find("h1", class_="title")
        if title_h1:
            title_text = title_h1.get_text(strip=True)
            prefix = "Title:"
            if title_text.startswith(prefix):
                title = title_text[len(prefix) :].strip()

        authors = []
        authors_div = soup.find("div", class_="authors")
        if authors_div:
            author_links = authors_div.find_all("a")
            for a in author_links:
                name = a.get_text(strip=True)
                if name:
                    authors.append(name)

        abstract = None
        abstract_header = soup.find("blockquote", class_="abstract")
        if abstract_header:
            text = abstract_header.get_text(separator=" ", strip=True)
            prefix = "Abstract:"
            if text.startswith(prefix):
                abstract = text[len(prefix) :].strip()
            else:
                abstract = text.strip()

        return ArxivPaper(
            title=title,
            abstract=abstract,
            authors=authors,
            url=self.arxiv_url,
            paper_id=self.arxiv_url.split("/")[-1],
            sections=[],
        )


def download_paper(paper_id: str) -> Path:
    destination = download_path(paper_id)
    destination.parent.mkdir(parents=True, exist_ok=True)

    pdf_url = f"https://arxiv.org/pdf/{paper_id}"
    response = requests.get(pdf_url)
    with open(destination, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)

    return destination


if __name__ == "__main__":
    url = "https://arxiv.org/abs/2508.18106"
    paper_scraper = ArxivPaperScraper(url)
    info = paper_scraper.scrape_arxiv_info()
    download_paper(info.paper_id)
