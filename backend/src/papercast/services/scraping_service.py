import requests
from bs4 import BeautifulSoup


def scrape_arxiv_info(arxiv_abs_url: str):
    res = requests.get(arxiv_abs_url)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, "html.parser")

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
            abstract = text[len(prefix):].strip()
        else:
            abstract = text.strip()

    return {
        "authors": authors,
        "abstract": abstract,
        "paper_id": arxiv_abs_url.split("/")[-1],
    }

if __name__ == "__main__":
    url = "https://arxiv.org/abs/2508.18106"
    info = scrape_arxiv_info(url)
    print(info)
