install-web:
	cd apps/web && npm install

run-web:
	cd apps/web && npm run dev

run-api:
	cd services/api && uvicorn app.main:app --reload --port 8000

test:
	cd services/api && pytest -q

compile:
	cd services/api && python -m compileall app tests
