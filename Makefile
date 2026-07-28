.SILENT:

.PHONY: start clean dev up build down clean_compose ps shapp logs zip

APP=app.main:app
HOST=0.0.0.0
PORT=8888
COMPOSE=docker compose

start:
	uvicorn $(APP) --host $(HOST) --port $(PORT)

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	clear

dev:
	uvicorn $(APP) --host $(HOST) --port $(PORT) --reload

up:
	$(COMPOSE) up -d

build:
	$(COMPOSE) up -d --build

down:
	$(COMPOSE) down

clean_compose:
	$(COMPOSE) down -v

ps:
	$(COMPOSE) ps -a

shapi:
	$(COMPOSE) exec api sh

logs:
	$(COMPOSE) logs -f api

zip:
	zip -r app.zip ./app -x "**cache__" "**venv**" "**vscode**" ".**" "**.md**" "dataset/**"