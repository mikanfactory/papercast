import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

import pymupdf
import pymupdf4llm


@dataclass(frozen=True)
class MarkdownChapter:
    title: str
    markdown: str
    start_page: Optional[int] = None
    end_page: Optional[int] = None


def calculate_pdf_page_count(file_path: str) -> int:
    doc = pymupdf.open(file_path)
    return len(doc)


def _extract_outline_ranges(
    file_path: str, level: int = 1
) -> List[Tuple[str, int, int]]:
    doc = pymupdf.open(file_path)
    toc = doc.get_toc()  # [[level, title, page1], ...]
    tops: List[Tuple[str, int]] = [
        (title, page1) for lv, title, page1 in toc if lv == level
    ]
    if not tops:
        return []

    ranges: List[Tuple[str, int, int]] = []
    for i, (title, start1) in enumerate(tops):
        s0 = max(0, start1 - 1)
        if i + 1 < len(tops):
            next_start1 = tops[i + 1][1]
            e0 = max(0, next_start1 - 2)
        else:
            e0 = doc.page_count - 1
        e0 = max(s0, e0)
        ranges.append((title.strip() or "chapter", s0, e0))
    return ranges


def to_markdown_by_outline(
    file_path: str,
    level: int = 1,
    *,
    embed_images: bool = False,
    write_images: bool = False,
    image_path: Optional[str] = None,
    image_format: str = "png",
    dpi: int = 200,
) -> List[MarkdownChapter]:
    ranges = _extract_outline_ranges(file_path, level=level)
    if not ranges:
        return []

    results: List[MarkdownChapter] = []
    for title, s0, e0 in ranges:
        pages = list(range(s0, e0 + 1))
        md = pymupdf4llm.to_markdown(
            file_path,
            pages=pages,
            embed_images=embed_images,
            write_images=False if embed_images else write_images,
            image_path=image_path,
            image_format=image_format,
            dpi=dpi,
        )
        results.append(
            MarkdownChapter(title=title, markdown=md, start_page=s0, end_page=e0)
        )
    return results


def _split_markdown_by_headings(
    md: str, *, min_level: int = 1
) -> List[Tuple[str, str]]:
    parts: List[Tuple[str, str]] = []
    pat = re.compile(rf"^(?P<hash>\#+)\s+(?P<title>.+)$")

    cur_title = "preamble"
    buf: list[str] = []

    for line in md.splitlines():
        m = pat.match(line)
        if m and len(m.group("hash")) >= min_level:
            if buf:
                parts.append((cur_title, "\n".join(buf)))
                buf = []
            cur_title = m.group("title").strip()
        buf.append(line)

    if buf:
        parts.append((cur_title, "\n".join(buf)))

    return parts


def to_markdown_by_headings(
    file_path: str,
    *,
    min_level: int = 1,
    embed_images: bool = False,
    write_images: bool = False,
    image_path: Optional[str] = None,
    image_format: str = "png",
    dpi: int = 200,
) -> List[MarkdownChapter]:
    md = pymupdf4llm.to_markdown(
        file_path,
        embed_images=embed_images,
        write_images=False if embed_images else write_images,
        image_path=image_path,
        image_format=image_format,
        dpi=dpi,
    )

    chapters = _split_markdown_by_headings(md, min_level=min_level)
    return [
        MarkdownChapter(title=t or "section", markdown=chunk) for t, chunk in chapters
    ]


if __name__ == "__main__":
    sample = "downloads/2509.01106v1.pdf"
    # sample = "downloads/2509.02547v1.pdf"
    # print("page_count:", calculate_pdf_page_count(sample))

    # print("\n-- Outline level=1 --")
    # for ch in to_markdown_by_outline(sample, level=1, embed_images=False):
    #     print(ch.start_page, ch.end_page, ch.title)
    #     print(ch.markdown[:200].replace("\n", " "), "...\n")
    #
    print("\n-- Headings min_level=1 --")
    for ch in to_markdown_by_headings(sample, min_level=2):
        print(ch.title)
        print(ch.markdown[:200].replace("\n", " "), "...\n")
