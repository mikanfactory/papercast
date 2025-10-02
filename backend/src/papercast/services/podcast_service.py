from logging import getLogger
from pathlib import Path

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langgraph.func import entrypoint, task
from pydantic import BaseModel, ConfigDict, Field

from papercast.entities.arxiv_paper import ArxivPaper, ArxivSection
from papercast.services.markdown_parser import MarkdownParser

logger = getLogger(__name__)
MAX_RETRY_COUNT = 3

GEMINI_LIGHT_MODEL = "gemini-2.5-flash"
GEMINI_HEAVY_MODEL = "gemini-2.5-pro"
OPENAI_MODEL = "gpt-5"


class FilterResult(BaseModel):
    is_target: bool = Field(..., description="対象の論文か否か")


class SectionSummary(BaseModel):
    section: ArxivSection = Field(..., description="セクション")
    summary: str = Field(..., description="セクションの要約")


class PodcastScriptWritingResult(BaseModel):
    script: str = Field(..., description="生成されたポッドキャストの台本")


class EvaluateResult(BaseModel):
    is_valid: bool = Field(..., description="適切か否か")
    feedback_message: str = Field(..., description="フィードバックメッセージ")


class ScriptWritingWorkflowInput(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    paper: ArxivPaper
    markdown_parser: MarkdownParser
    gemini_light_model: ChatGoogleGenerativeAI
    gemini_heavy_model: ChatGoogleGenerativeAI
    openai_model: ChatOpenAI


SectionSummaries = dict[str, SectionSummary]
MissingInfos = list[tuple[ArxivSection, str]]


def load_prompt(name: str) -> str:
    prompt_path = Path(__file__).parent / "prompts" / f"{name}.txt"
    return prompt_path.read_text().strip()


@task
async def is_relevant_paper(paper: ArxivPaper, llm) -> bool:
    prompt = load_prompt("is_relevant_paper")
    message = ChatPromptTemplate(
        [
            ("human", prompt),
        ]
    )
    chain = message | llm | StrOutputParser()
    result = await chain.ainvoke(
        {
            "title": paper.title,
            "authors": ", ".join(paper.authors),
            "abstract": paper.abstract,
        }
    )
    return result.lower() == "yes"


@task
async def summarize_sections(paper: ArxivPaper, markdown_parser: MarkdownParser, llm) -> SectionSummaries:
    prompt = load_prompt("summarize_sections")

    summaries = {}
    # TODO: levelを可変にする
    for section in markdown_parser.extract_sections_by_outline(level=1):
        logger.info(f"summarize section for {section.section_level_name}: {section.title}...")
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
                "authors": ", ".join(paper.authors),
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
    logger.info(f"Writing script for paper: {paper.title}")
    prompt = load_prompt("write_script")
    if feedback_messages:
        feedback_text = "\n".join([f"- {msg}" for msg in feedback_messages])
        prompt += f"\n\n<feedback>\n{feedback_text}\n</feedback>"

    message = ChatPromptTemplate(
        [
            ("human", prompt),
        ]
    )
    chain = message | llm.with_structured_output(PodcastScriptWritingResult)
    summaries_text = "\n".join([f"{s.section.title}\n{s.summary}\n\n" for s in summaries.values()])
    script = await chain.ainvoke(
        {
            "title": paper.title,
            "authors": ", ".join(paper.authors),
            "abstract": paper.abstract,
            "summaries": summaries_text,
        }
    )
    return script


@task
async def evaluate_script(paper: ArxivPaper, script: str, llm) -> EvaluateResult:
    prompt = load_prompt("evaluate_script")
    message = ChatPromptTemplate(
        [
            ("human", prompt),
        ]
    )
    chain = message | llm.with_structured_output(EvaluateResult)
    result = await chain.ainvoke(
        {
            "title": paper.title,
            "authors": ", ".join(paper.authors),
            "abstract": paper.abstract,
            "script": script,
        }
    )
    return result


@entrypoint()
async def script_writing_workflow(inputs: ScriptWritingWorkflowInput) -> str | None:
    relevance = await is_relevant_paper(inputs.paper, inputs.gemini_light_model)
    if not relevance:
        logger.info(f"Paper is not relevant: {inputs.paper.title}")
        return None

    summaries = await summarize_sections(inputs.paper, inputs.markdown_parser, inputs.gemini_light_model)

    feedback_messages = []
    retry_count = 0
    script = ""

    while retry_count < MAX_RETRY_COUNT:
        script = await write_script(inputs.paper, summaries, feedback_messages, inputs.openai_model)
        evaluation = await evaluate_script(inputs.paper, script, inputs.gemini_heavy_model)

        if evaluation.is_valid:
            return script

        feedback_messages.append(evaluation.feedback_message)
        retry_count += 1

    return script
