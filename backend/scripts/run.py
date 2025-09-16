from papercast.services.markdown_parser import to_markdown_by_outline, to_markdown_by_headings

def main():
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


if __name__ == "__main__":
    main()
