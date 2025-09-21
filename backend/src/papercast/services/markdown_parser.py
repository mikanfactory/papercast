from functools import partial
from itertools import pairwise

import pymupdf
import pymupdf4llm

from papercast.entities.arxiv_paper import ArxivSection


def _extract_lines(text: str, marker: str, keep: str) -> str:
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if marker in line:
            if keep == "before":
                return "\n".join(lines[:i])
            elif keep == "after":
                return "\n".join(lines[i + 1 :])
    return text


extract_before = partial(_extract_lines, keep="before")
extract_after = partial(_extract_lines, keep="after")


class MarkdownParser:
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.doc = pymupdf.open(pdf_path)
        self.page_count = self.doc.page_count

    def extract_all_sections_by_outline(self) -> list[ArxivSection]:
        return self.extract_sections_by_outline()

    def extract_sections_by_outline(self, level: int | None = None) -> list[ArxivSection]:
        toc: list[list] = self.doc.get_toc(simple=False) or []
        if level:
            toc = [item for item in toc if item[0] == level]

        if not toc:
            raise ValueError("The document has no outline (table of contents).")

        sections = []
        for prev, nxt in pairwise(toc):
            section = ArxivSection(
                title=prev[1],
                level=prev[0],
                section_level_name=prev[3]["nameddest"],
                start_page=prev[3]["page"],
                end_page=nxt[3]["page"],
                next_section_title=nxt[1],
            )
            sections.append(section)
        return sections

    def extract_markdown_text(self, section: ArxivSection) -> str:
        start, end = int(section.start_page), int(section.end_page)
        pages = list(range(start, end + 1))  # end is inclusive
        md = pymupdf4llm.to_markdown(
            self.doc,
            pages=pages,
            ignore_graphics=True,
            ignore_images=True,
            ignore_code=True,
        )
        md = extract_after(md, section.title)
        md = extract_before(md, section.next_section_title)
        return md

    def read_all(self):
        md = pymupdf4llm.to_markdown(
            self.doc,
            ignore_graphics=True,
            ignore_images=True,
            ignore_code=True,
        )
        return md


if __name__ == "__main__":
    # sample = "downloads/2509.01106v1.pdf"
    sample = "downloads/2509.02547v1.pdf"

    parser = MarkdownParser(sample)
    # for sec in parser.extract_sections_by_outline()[:2]:
    #     print(sec.title)
    #     print(parser.extract_markdown_text(sec))
    #     print("**********************************************")
    print(parser.extract_sections_by_outline(level=None))
