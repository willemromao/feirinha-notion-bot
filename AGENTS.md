# Repository Guidelines

## Project Structure & Module Organization
- `src/` contains the Lambda application code.
- `src/lambda_handler.py` is the AWS Lambda entrypoint.
- `src/telegram/`, `src/processing/`, `src/notion/`, and `src/storage/` hold integration and domain modules (Telegram I/O, receipt parsing/OpenAI, Notion writes, DynamoDB deduplication).
- `scripts/` contains operational helpers (`setup-webhook.sh`, `delete-webhook.sh`, `validate-credentials.py`).
- `template.yaml` defines AWS SAM infrastructure (Lambda, HTTP API, DynamoDB).
- `event.example.json` is the local invocation payload example.

## Build, Test, and Development Commands
- `python3 -m venv .venv && source .venv/bin/activate` creates a local environment.
- `pip install -r requirements.txt` installs root dependencies for scripts and local tooling.
- `sam build` builds the serverless app.
- `sam deploy --guided` performs first-time deployment and stores settings in `samconfig.toml`.
- `sam build && sam deploy` deploys subsequent changes.
- `sam local invoke TelegramBotFunction -e event.example.json` runs local Lambda smoke tests.
- `python scripts/validate-credentials.py` checks Telegram, OpenAI, and Notion credentials before deploy.
- `sam logs -n TelegramBotFunction --tail` tails production logs.

## Coding Style & Naming Conventions
- Use Python 3.12 style with 4-space indentation.
- Follow existing naming: modules/functions in `snake_case`, classes in `PascalCase`, constants in `UPPER_SNAKE_CASE`.
- Keep functions focused and log key operational events with `logging`.
- Prefer type hints in public methods and data-shaping code (see `src/telegram/handler.py`).

## Testing Guidelines
- There is no formal automated test suite yet; validate changes with:
  - local invoke (`sam local invoke ...`)
  - credential validation script
  - targeted webhook/manual flow checks.
- For new parsing/business logic, add unit tests under `tests/` mirroring `src/` paths (example: `tests/processing/test_receipt_parser.py`).

## Commit & Pull Request Guidelines
- Use Conventional Commit prefixes seen in history: `feat:`, `fix:` (imperative, concise summary).
- Keep commits focused by concern (infrastructure, parser logic, integrations).
- PRs should include:
  - what changed and why
  - deployment/config impact (`template.yaml`, env vars, secrets)
  - evidence of validation (local invoke output, logs, or webhook test result).

## Security & Configuration Tips
- Never commit real secrets; use `.env.example`/`.env.local.example` as templates only.
- Treat webhook tokens, API keys, and Notion IDs as sensitive.
- Prefer SAM parameters (`NoEcho`) for production secrets.
