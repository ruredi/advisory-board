.PHONY: dev api dashboard

api:
	.venv/bin/python -m uvicorn api.main:app --reload --host 127.0.0.1 --port 8100

dashboard:
	cd dashboard && npm run dev

dev:
	$(MAKE) -j2 api dashboard
