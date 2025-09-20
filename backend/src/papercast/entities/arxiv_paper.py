from pydantic import BaseModel, Field


class ArxivSection(BaseModel):
    title: str = Field(..., description="セクションのタイトル")
    level: int = Field(..., description="セクションのレベル（アウトラインの階層）")
    section_level_name: str = Field(..., description="セクションのレベル名（アウトラインの階層名）")
    start_page: int = Field(..., description="セクションの開始ページ（0始まり）")
    end_page: int = Field(..., description="セクションの終了ページ（0始まり）")
    next_section_title: str = Field(..., description="次のセクションのタイトル（終了ページの決定に使用）")

    @property
    def section_title_with_level(self) -> str:
        return f"{self.section_level_name} {self.title}"


class ArxivPaper(BaseModel):
    id: int | None = Field(default=None, description="論文のID（データベース上のID）")
    title: str = Field(..., description="論文のタイトル")
    abstract: str = Field(..., description="論文のアブストラクト")
    authors: list[str] = Field(..., description="著者のリスト")
    url: str = Field(..., description="論文のURL")
    paper_id: str = Field(..., description="論文のID")
    sections: list[ArxivSection] = Field(..., description="論文のセクションリスト")
