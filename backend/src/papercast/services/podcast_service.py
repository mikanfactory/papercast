from logging import getLogger
from pathlib import Path

from langchain_core.prompts import ChatPromptTemplate
from langgraph.func import entrypoint, task
from pydantic import BaseModel, Field

from papercast.entities.arxiv_paper import ArxivPaper, ArxivSection
from papercast.services.markdown_parser import MarkdownParser

logger = getLogger(__name__)
MAX_RETRY_COUNT = 3

GEMINI_MODEL = "gemini-2.5-flash"


class SectionSummary(BaseModel):
    section: ArxivSection = Field(..., description="セクション")
    summary: str = Field(..., description="セクションの要約")


class PodcastScriptWritingResult(BaseModel):
    script: str = Field(..., description="生成されたポッドキャストの台本")
    missing_infos: list[tuple[ArxivSection, str]] = Field(..., description="台本に反映されなかった情報のリスト")


class EvaluateResult(BaseModel):
    is_valid: bool = Field(..., description="適切か否か")
    feedback_message: str = Field(..., description="フィードバックメッセージ")


SectionSummaries = dict[str, SectionSummary]
MissingInfos = list[tuple[ArxivSection, str]]


def load_prompt(name: str) -> str:
    prompt_path = Path(__file__).parent / "prompts" / f"{name}.txt"
    return prompt_path.read_text().strip()


@task
async def summarize_sections(paper: ArxivPaper, markdown_parser: MarkdownParser, llm) -> SectionSummaries:
    prompt = load_prompt("summarize_sections")

    summaries = {}
    for section in paper.sections:
        content = markdown_parser.extract_markdown_text(section)
        message = ChatPromptTemplate(
            [
                ("human", prompt),
            ]
        )
        chain = message | llm.with_structured_output(SectionSummary)
        summary = await chain.ainvoke(
            {
                "title": paper.title,
                "abstract": paper.abstract,
                "section_title": section.title,
                "section_content": content,
            }
        )
        summaries[section.section_level_name] = summary

    return summaries


@task
async def write_script(
    paper: ArxivPaper,
    summaries: SectionSummaries,
    feedback_messages: list[str],
    llm,
) -> str:
    prompt = load_prompt("write_script")
    if feedback_messages:
        feedback_text = "\n".join([f"- {msg}" for msg in feedback_messages])
        prompt += f"\n\n# フィードバック\n{feedback_text}"

    message = ChatPromptTemplate(
        [
            ("human", prompt),
        ]
    )
    chain = message | llm.with_structured_output(PodcastScriptWritingResult)
    summaries_text = "\n".join([f"{s.section.title}: {s.summary}" for s in summaries.values()])
    script = await chain.ainvoke(
        {
            "title": paper.title,
            "abstract": paper.abstract,
            "summaries": summaries_text,
        }
    )
    return script


@task
async def refine_summaries(
    paper: ArxivPaper,
    summaries: SectionSummaries,
    missing_infos: list[tuple[ArxivSection, str]],
    llm,
) -> SectionSummaries:
    prompt = load_prompt("refine_summaries")

    for section, missing_info in missing_infos:
        message = ChatPromptTemplate(
            [
                ("human", prompt),
            ]
        )
        chain = message | llm.with_structured_output(SectionSummary)
        refined_summary = await chain.ainvoke(
            {
                "title": paper.title,
                "abstract": paper.abstract,
            }
        )
        summaries[section.section_level_name] = refined_summary

    return summaries


@task
async def evaluate_script(script: str, llm) -> EvaluateResult:
    prompt = load_prompt("evaluate_script")
    message = ChatPromptTemplate(
        [
            ("human", prompt),
        ]
    )
    chain = message | llm.with_structured_output(EvaluateResult)
    result = await chain.ainvoke(
        {
            "script": script,
        }
    )
    return result


@entrypoint()
async def script_writing_workflow(paper: ArxivPaper, markdown_parser: MarkdownParser, llm):
    summaries = await summarize_sections(paper, markdown_parser, llm)

    feedback_messages = []
    retry_count = 0
    script = ""

    while retry_count < MAX_RETRY_COUNT:
        script, missing_infos = await write_script(paper, summaries, feedback_messages, llm)
        if missing_infos:
            summaries = refine_summaries(paper, summaries, missing_infos, llm)

        evaluation = await evaluate_script(script, llm)

        if evaluation.is_valid:
            return script

        feedback_messages.append(evaluation.feedback_message)
        retry_count += 1

    return script
