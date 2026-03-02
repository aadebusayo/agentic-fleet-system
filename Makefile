SHELL := /bin/bash

.PHONY: bootstrap test lint security-scan infra-validate fmt

bootstrap:
	cd backend && python -m pip install -e .[dev]
	cd sandbox-agent && python -m pip install -e .[dev]
	cd control-plane && npm install
	cd agent-fleet && go mod tidy

test:
	cd backend && pytest -q
	cd sandbox-agent && pytest -q
	cd control-plane && npm test
	cd agent-fleet && go test ./...

lint:
	cd backend && ruff check src tests
	cd sandbox-agent && ruff check src tests
	cd control-plane && npm run lint
	cd agent-fleet && go vet ./...

fmt:
	cd backend && ruff format src tests
	cd sandbox-agent && ruff format src tests
	cd control-plane && npm run format
	cd agent-fleet && go fmt ./...

security-scan:
	cd backend && pip-audit || true
	cd sandbox-agent && pip-audit || true
	cd control-plane && npm audit --audit-level=high || true
	cd infra/terraform && terraform fmt -check -recursive

infra-validate:
	cd infra/terraform/environments/dev && terraform init -backend=false
	cd infra/terraform/environments/dev && terraform validate
