import asyncio

from langchain_core.runnables.config import RunnableConfig
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langgraph.func import entrypoint
from pydantic import BaseModel, ConfigDict

from papercast.config import GEMINI_API_KEY
from papercast.entities.arxiv_paper import ArxivPaper
from papercast.repositories.arxiv_paper_repository import ArxivPaperRepository
from papercast.services import podcast_service as ps
from papercast.services.arxiv_paper_service import ArxivPaperService
from papercast.services.db import supabase_client
from papercast.services.markdown_parser import MarkdownParser


class SummarizeSectionInput(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    paper: ArxivPaper
    markdown_parser: MarkdownParser
    llm: ChatGoogleGenerativeAI


class WriteScriptInput(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    paper: ArxivPaper
    summaries: ps.SectionSummaries
    llm: ChatGoogleGenerativeAI


def create_arxiv_paper():
    url = "https://arxiv.org/abs/2508.18106"
    service = ArxivPaperService(ArxivPaperRepository(supabase_client))
    arxiv_paper = service.create_arxiv_paper(url)
    print(arxiv_paper)


def find_arxiv_paper(arxiv_paper_id=1):
    service = ArxivPaperService(ArxivPaperRepository(supabase_client))
    arxiv_paper = service.find_arxiv_paper(arxiv_paper_id)
    print(arxiv_paper)


@entrypoint()
async def _summarize_sections(inputs: SummarizeSectionInput):
    return await ps.summarize_sections(inputs.paper, inputs.markdown_parser, inputs.llm)


def summarize_sections(arxiv_paper_id=1, dump=False):
    service = ArxivPaperService(ArxivPaperRepository(supabase_client))
    paper = service.find_arxiv_paper(arxiv_paper_id)

    markdown_parser = MarkdownParser(pdf_path=paper.download_path)

    gemini_model = "gemini-2.5-flash"
    llm = ChatGoogleGenerativeAI(model=gemini_model, api_key=GEMINI_API_KEY, temperature=0.2)

    summaries = asyncio.run(
        _summarize_sections.ainvoke(
            SummarizeSectionInput(paper=paper, markdown_parser=markdown_parser, llm=llm),
            config=RunnableConfig(run_name="Summarize Sections"),
        )
    )

    if not dump:
        for key, summary in summaries.values():
            print(key)
            print(summary)

    return summaries


@entrypoint()
async def _write_script(inputs: WriteScriptInput):
    return await ps.write_script(inputs.paper, inputs.summaries, [], inputs.llm)


def write_script(arxiv_paper_id=1):
    service = ArxivPaperService(ArxivPaperRepository(supabase_client))
    paper = service.find_arxiv_paper(arxiv_paper_id)

    summaries = summarize_sections(arxiv_paper_id)

    gemini_model = "gemini-2.5-flash"
    llm = ChatGoogleGenerativeAI(model=gemini_model, api_key=GEMINI_API_KEY, temperature=0.2)
    script = asyncio.run(
        _write_script.ainvoke(
            WriteScriptInput(paper=paper, summaries=summaries, llm=llm), config=RunnableConfig(run_name="Write Script")
        )
    )
    print("=============================================")
    print(script)


def run_workflow(arxiv_paper_id=1):
    service = ArxivPaperService(ArxivPaperRepository(supabase_client))
    paper = service.find_arxiv_paper(arxiv_paper_id)

    markdown_parser = MarkdownParser(pdf_path=paper.download_path)

    gemini_light_model = ChatGoogleGenerativeAI(model="gemini-2.5-flash", api_key=GEMINI_API_KEY, temperature=0.2)
    gemini_heavy_model = ChatGoogleGenerativeAI(model="gemini-2.5-pro", api_key=GEMINI_API_KEY, temperature=0.2)
    openai_model = ChatOpenAI(model="gpt-5", temperature=0.2)

    script = asyncio.run(
        ps.script_writing_workflow.ainvoke(
            ps.ScriptWritingWorkflowInput(
                paper=paper,
                markdown_parser=markdown_parser,
                gemini_light_model=gemini_light_model,
                gemini_heavy_model=gemini_heavy_model,
                openai_model=openai_model,
            ),
            config=RunnableConfig(run_name="Script Writing"),
        )
    )
    print(script)


def main():
    run_workflow(1)


if __name__ == "__main__":
    main()
