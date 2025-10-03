from papercast.entities import ArxivPaper


class ArxivPaperRepository:
    def __init__(self, db):
        self.db = db

    def find(self, arxiv_paper_id: int) -> ArxivPaper:
        response = self.db.table("arxiv_paper").select("*").eq("id", arxiv_paper_id).execute()
        if len(response.data):
            return ArxivPaper(**response.data[0])
        raise ValueError(f"ArxivPaper id {arxiv_paper_id} not found")

    def select_all(self) -> list[ArxivPaper]:
        response = self.db.table("arxiv_paper").select("*").execute()
        if len(response.data):
            return [ArxivPaper(**item) for item in response.data]
        return []

    def create(self, arxiv_paper: ArxivPaper) -> ArxivPaper:
        exclude_fields = {"id", "created_at", "updated_at"}
        response = self.db.table("arxiv_paper").insert(arxiv_paper.model_dump(exclude=exclude_fields)).execute()
        if len(response.data) == 1:
            return ArxivPaper(**response.data[0])
        raise RuntimeError(f"Failed to create arxiv_paper: {arxiv_paper}, response: {response}")

    def update(self, arxiv_paper: ArxivPaper) -> ArxivPaper:
        exclude_fields = {"id", "created_at", "updated_at"}
        response = (
            self.db.table("arxiv_paper")
            .update(arxiv_paper.model_dump(exclude=exclude_fields))
            .eq("id", arxiv_paper.id)
            .execute()
        )
        if len(response.data):
            return ArxivPaper(**response.data[0])
        raise RuntimeError(f"Failed to update arxiv_paper: {arxiv_paper}, response: {response}")
