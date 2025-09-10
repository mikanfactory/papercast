from enum import Enum
import asyncio
from logging import getLogger

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.func import entrypoint, task
from pydantic import BaseModel, Field

from papercast.config import GEMINI_API_KEY

logger = getLogger(__name__)
MAX_RETRY_COUNT = 3

GEMINI_MODEL = "gemini-2.5-flash"


class ArxivPaper(BaseModel):
    title: str = Field(..., description="論文のタイトル")
    abstract: str = Field(..., description="論文のアブストラクト")
    authors: list[str] = Field(..., description="著者のリスト")
    url: str = Field(..., description="論文のURL")


class TopicTitle(Enum):
    APPETIZER = "Appetizer"
    MAIN_DISH = "Main Dish"
    LAST_DISH = "Last Dish"

    @property
    def prompt(self) -> str:
        if self == TopicTitle.APPETIZER:
            return "序論、背景、関連研究"
        elif self == TopicTitle.MAIN_DISH:
            return "手法、実験、結果"
        elif self == TopicTitle.LAST_DISH:
            return "考察、結論、今後の展望"
        else:
            raise ValueError("Invalid TopicTitle")


class PodcastTopic(BaseModel):
    title: TopicTitle = Field(..., description="トピックのタイトル")
    sections: list[int] = Field(..., description="トピックのセクションリスト")


class PodcastTopicSummary(BaseModel):
    title: TopicTitle = Field(..., description="トピックのタイトル")
    sections: list[int] = Field(..., description="トピックのセクションリスト")
    summary: str = Field(..., description="トピックの要約")


class EvaluateResult(BaseModel):
    is_valid: bool = Field(..., description="適切か否か")
    feedback_message: str = Field(..., description="フィードバックメッセージ")


@task
async def select_sections(
    paper: ArxivPaper, topic_title: TopicTitle, llm
) -> PodcastTopic:
    prompt_text = """
    """
    message = ChatPromptTemplate(
        [
            ("human", prompt_text),
        ]
    )
    chain = message | llm.with_structured_output(StrOutputParser())
    topic = await chain.ainvoke({})
    return topic


@task
async def summarize_topic(
    paper: ArxivPaper, topic: PodcastTopic, llm
) -> PodcastTopicSummary:
    prompt_text = """
    """
    message = ChatPromptTemplate(
        [
            ("human", prompt_text),
        ]
    )
    chain = message | llm.with_structured_output(StrOutputParser())
    script = await chain.ainvoke({})
    return script


@task
async def write_script(
    paper: ArxivPaper,
    summaries: list[PodcastTopicSummary],
    feedback_messages: list[str],
    llm,
) -> str:
    prompt_text = """
    """
    message = ChatPromptTemplate(
        [
            ("human", prompt_text),
        ]
    )
    chain = message | llm.with_structured_output(StrOutputParser())
    script = await chain.ainvoke({})
    return script


@task
async def evaluate_script(script: str, llm) -> EvaluateResult:
    prompt_text = """
    """
    message = ChatPromptTemplate(
        [
            ("human", prompt_text),
        ]
    )
    chain = message | llm.with_structured_output(StrOutputParser())
    result = await chain.ainvoke({})
    return result


@entrypoint()
async def script_writing_workflow(paper: ArxivPaper, llm):
    topics = []
    for title in TopicTitle:
        topic = await select_sections(paper, title, llm)
        topics.append(topic)

    summaries = []
    for topic in topics:
        summary = await summarize_topic(paper, topic, llm)
        summaries.append(summary)

    feedback_messages = []
    retry_count = 0

    while retry_count < MAX_RETRY_COUNT:
        script = await write_script(paper, summaries, feedback_messages, llm)
        evaluation = await evaluate_script(script, llm)

        if evaluation.is_valid:
            return script

        feedback_messages.append(evaluation.feedback_message)
        retry_count += 1
