SHELL := /bin/bash

COMPOSE := docker compose
LOCAL_COMPOSE := docker-compose.local.yml
PROD_COMPOSE := docker-compose.yml
LOCAL_ENV := .env.local
LOCAL_ENV_EXAMPLE := .env.local.example
PROD_ENV := .env.prod
PROD_ENV_EXAMPLE := .env.prod.example

.PHONY: dev-mac dev-windows dev-core prod down-local down-prod validate-local-mac validate-local-windows validate-local-core validate-prod test-mcp ensure-local-env ensure-prod-env

ensure-local-env:
	@if [[ ! -f "$(LOCAL_ENV)" ]]; then cp "$(LOCAL_ENV_EXAMPLE)" "$(LOCAL_ENV)"; fi
	@mkdir -p secrets
	@if [[ ! -f secrets/1password-credentials.json ]]; then cp secrets/1password-credentials.json.example secrets/1password-credentials.json; fi

ensure-prod-env:
	@if [[ ! -f "$(PROD_ENV)" ]]; then cp "$(PROD_ENV_EXAMPLE)" "$(PROD_ENV)"; fi

dev-mac: ensure-local-env
	@LOCAL_LLM_BASE_URL=http://ollama:11434 \
	LOCAL_LLM_MODEL="$$(awk -F= '/^OLLAMA_MODEL=/{print $$2}' $(LOCAL_ENV))" \
	$(COMPOSE) --env-file $(LOCAL_ENV) -f $(LOCAL_COMPOSE) --profile mac up -d --build

dev-windows: ensure-local-env
	@LOCAL_LLM_BASE_URL=http://vllm:8000/v1 \
	LOCAL_LLM_MODEL="$$(awk -F= '/^VLLM_MODEL=/{print $$2}' $(LOCAL_ENV))" \
	$(COMPOSE) --env-file $(LOCAL_ENV) -f $(LOCAL_COMPOSE) --profile windows up -d --build

# GPU-free smoke stack (Traefik, Alloy, Postgres, n8n, MCP bridge, Qdrant, 1Password Connect). Not the default dev path.
dev-core: ensure-local-env
	@$(COMPOSE) --env-file $(LOCAL_ENV) -f $(LOCAL_COMPOSE) --profile core up -d --build

prod: ensure-prod-env
	@$(COMPOSE) --env-file $(PROD_ENV) -f $(PROD_COMPOSE) up -d --remove-orphans

down-local: ensure-local-env
	@$(COMPOSE) --env-file $(LOCAL_ENV) -f $(LOCAL_COMPOSE) \
		--profile core --profile mac --profile windows down --remove-orphans

down-prod: ensure-prod-env
	@$(COMPOSE) --env-file $(PROD_ENV) -f $(PROD_COMPOSE) down --remove-orphans

validate-local-mac: ensure-local-env
	@LOCAL_LLM_BASE_URL=http://ollama:11434 \
	LOCAL_LLM_MODEL="$$(awk -F= '/^OLLAMA_MODEL=/{print $$2}' $(LOCAL_ENV))" \
	$(COMPOSE) --env-file $(LOCAL_ENV) -f $(LOCAL_COMPOSE) --profile mac config >/dev/null

validate-local-windows: ensure-local-env
	@LOCAL_LLM_BASE_URL=http://vllm:8000/v1 \
	LOCAL_LLM_MODEL="$$(awk -F= '/^VLLM_MODEL=/{print $$2}' $(LOCAL_ENV))" \
	$(COMPOSE) --env-file $(LOCAL_ENV) -f $(LOCAL_COMPOSE) --profile windows config >/dev/null

validate-local-core: ensure-local-env
	@$(COMPOSE) --env-file $(LOCAL_ENV) -f $(LOCAL_COMPOSE) --profile core config >/dev/null

validate-prod: ensure-prod-env
	@$(COMPOSE) --env-file $(PROD_ENV) -f $(PROD_COMPOSE) config >/dev/null

test-mcp:
	@python3 -m pytest mcp-servers/n8n-bridge/tests -q
