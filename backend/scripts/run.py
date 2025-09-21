import asyncio
from langchain_google_genai import ChatGoogleGenerativeAI

from papercast.config import GEMINI_API_KEY
from papercast.repositories.arxiv_paper_repository import ArxivPaperRepository
from papercast.services.arxiv_paper_service import ArxivPaperService
from papercast.services.markdown_parser import MarkdownParser
from papercast.services.db import supabase_client
from papercast.services.podcast_service import script_writing_workflow


def create_arxiv_paper():
    url = "https://arxiv.org/abs/2508.18106"
    service = ArxivPaperService(ArxivPaperRepository(supabase_client))
    arxiv_paper = service.create_arxiv_paper(url)
    print(arxiv_paper)


def find_arxiv_paper(id=1):
    service = ArxivPaperService(ArxivPaperRepository(supabase_client))
    arxiv_paper = service.find_arxiv_paper(id)
    print(arxiv_paper)


def create_podcast():
    service = ArxivPaperService(ArxivPaperRepository(supabase_client))
    paper = service.find_arxiv_paper(arxiv_paper_id=1)

    gemini_model = "gemini-2.5-flash"
    llm = ChatGoogleGenerativeAI(model=gemini_model, api_key=GEMINI_API_KEY, temperature=0.2)

    markdown_parser = MarkdownParser(pdf_path=paper.download_path)

    script = asyncio.run(
        script_writing_workflow.ainvoke(
            {"paper": paper, "markdown_parser": markdown_parser, "llm": llm},
            config={"run_name": "ScriptWritingAgent"},
        )
    )
    print(script)


def main():
    find_arxiv_paper()


if __name__ == "__main__":
    main()
