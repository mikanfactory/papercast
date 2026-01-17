import pytest

from papercast.entities import ArxivPaper, ArxivPaperStatus
from papercast.repositories import ArxivPaperRepository


@pytest.fixture
def arxiv_paper_repository(supabase_client):
    return ArxivPaperRepository(supabase_client)


class TestArxivPaperRepository:
    @pytest.mark.integration
    def test_find_existing_paper(self, arxiv_paper_repository, initialized_paper):
        paper = arxiv_paper_repository.find(initialized_paper.id)

        assert paper.id == initialized_paper.id
        assert paper.title == initialized_paper.title
        assert paper.paper_id == initialized_paper.paper_id

    @pytest.mark.integration
    def test_find_nonexistent_paper_raises_error(self, arxiv_paper_repository):
        with pytest.raises(ValueError, match="ArxivPaper id 999999 not found"):
            arxiv_paper_repository.find(999999)

    @pytest.mark.integration
    def test_select_all(self, arxiv_paper_repository, initialized_paper):
        papers = arxiv_paper_repository.select_all()

        assert len(papers) >= 1
        assert all(isinstance(p, ArxivPaper) for p in papers)

    @pytest.mark.integration
    def test_select_target_papers(self, arxiv_paper_repository, script_created_paper):
        papers = arxiv_paper_repository.select_target_papers(script_created_paper.target_date)

        assert len(papers) >= 1
        for paper in papers:
            assert paper.script != ""

    @pytest.mark.integration
    def test_create(self, arxiv_paper_repository, sample_arxiv_paper):
        sample_arxiv_paper.paper_id = "2401.99999"
        sample_arxiv_paper.url = "https://arxiv.org/abs/2401.99999"

        created_paper = arxiv_paper_repository.create(sample_arxiv_paper)

        assert created_paper.id is not None
        assert created_paper.title == sample_arxiv_paper.title
        assert created_paper.paper_id == sample_arxiv_paper.paper_id

    @pytest.mark.integration
    def test_update(self, arxiv_paper_repository, initialized_paper):
        paper = arxiv_paper_repository.find(initialized_paper.id)

        paper.status = ArxivPaperStatus.script_created
        paper.script = "Speaker1: Test script."

        updated_paper = arxiv_paper_repository.update(paper)

        assert updated_paper.id == paper.id
        assert updated_paper.status == ArxivPaperStatus.script_created
        assert updated_paper.script == "Speaker1: Test script."
