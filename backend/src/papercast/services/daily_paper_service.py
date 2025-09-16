import re
import requests
from bs4 import BeautifulSoup
from typing import List, Tuple, Optional

def get_daily_papers_urls(date: str) -> List[str]:
    base = "https://huggingface.co/papers/date/"
    url = base + date
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


def get_papers_with_arxiv_ids(date: str):
    urls = get_daily_papers_urls(date)

    pattern = r"\b(\d{4}\.\d{5})\b"
    ids = set()
    for url in urls:
        match = re.search(pattern, url)
        if match:
            ids.add(match.group(1))

    return ids


if __name__ == "__main__":
    date = "2025-09-17"
    papers = get_papers_with_arxiv_ids(date)
    print(papers)
