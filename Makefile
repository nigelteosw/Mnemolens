PLUGIN_DIR := plugins/mnemolens
SERVER_DIR := $(PLUGIN_DIR)/server
UV := $(shell command -v uv 2>/dev/null)

.PHONY: bootstrap dev mcp test inspect-db

bootstrap:
	$(PLUGIN_DIR)/scripts/bootstrap

dev:
ifndef UV
	$(error uv is required for make dev. Install uv or run make bootstrap for the venv fallback)
endif
	PYTHONPATH=$(SERVER_DIR) uv run --project $(SERVER_DIR) python -m mnemolens.server

mcp:
	$(PLUGIN_DIR)/scripts/mnemolens-mcp

test:
ifdef UV
	PYTHONPATH=$(SERVER_DIR) uv run --project $(SERVER_DIR) --with pytest pytest $(SERVER_DIR)/tests
else
	PYTHONPATH=$(SERVER_DIR) $(SERVER_DIR)/.venv/bin/python -m pytest $(SERVER_DIR)/tests
endif

inspect-db:
	sqlite3 "$${MNEMOLENS_DB_PATH:-$${HOME}/.codex/mnemolens/mnemolens.sqlite3}"
