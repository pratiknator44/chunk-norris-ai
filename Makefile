.PHONY: setup dev test lint gen-client

setup:
	cd backend && uv sync
	cd frontend && npm install

dev:
	@trap 'kill 0' INT TERM; \
	(cd backend && uv run fastapi dev app/main.py) & \
	(cd frontend && npm run dev) & \
	wait

test:
	cd backend && uv run pytest
	cd frontend && npm run test --if-present

lint:
	cd backend && uv run ruff check . && uv run mypy app
	cd frontend && npm run lint && npm run typecheck

gen-client:
	cd frontend && npx openapi-typescript http://localhost:8000/openapi.json -o src/lib/api/schema.d.ts
