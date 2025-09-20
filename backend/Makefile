.PHONY: lint
lint:
	uv run ruff check src tests

.PHONY: format
format:
	uv run ruff format src tests && uv run ruff check --fix src tests

.PHONY: test
test:
	uv run pytest tests

.PHONY: test/integration
test/integration:
	uv run pytest -m integration tests

.PHONY: db/start
db/start:
	supabase start \
	  --exclude gotrue,realtime,storage-api,imgproxy,kong, \
				postgres-meta, \
				studio,edge-runtime,logflare,vector


.PHONY: db/clean
db/clean:
	supabase db reset --local --yes
