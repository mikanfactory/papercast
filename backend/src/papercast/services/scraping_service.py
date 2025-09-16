import requests
from bs4 import BeautifulSoup


def scrape_paper_info(url: str):
    res = requests.get(url)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, "html.parser")

    # 著者リスト
    authors = [a.get_text(strip=True) for a in soup.select("div:contains('Authors:') ~ a, div:contains('Authors:') ~ span")]

    # アブストラクト
    abstract_tag = soup.find("h2", string="Abstract")
    abstract = abstract_tag.find_next("p").get_text(strip=True) if abstract_tag else None

    # PDFリンク
    pdf_link = None
    pdf_tag = soup.find("a", string="View PDF")
    if pdf_tag:
        pdf_link = pdf_tag["href"]

    return {
        "authors": authors,
        "abstract": abstract,
        "pdf_link": pdf_link,
    }


if __name__ == "__main__":
    url = "https://huggingface.co/papers/2508.18106"
    info = scrape_paper_info(url)
    print(info)
