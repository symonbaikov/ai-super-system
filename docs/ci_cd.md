# CI/CD — Phase VIII

The repository now includes a GitHub Actions workflow (`.github/workflows/ci.yml`) that runs on every push and pull request targeting `main`. The workflow consists of four jobs:

1. **Backend (pytest):** Installs Python 3.11 dependencies from `backend/requirements.txt` and runs the FastAPI/AI integration test suite via `python -m pytest backend/tests`.
2. **Worker (Node tests):** Uses Node 20, installs `backend/package.json` dependencies with `npm ci`, and executes the legacy Node worker tests with `npm test`.
3. **Web (Vitest & build):** Uses Node 20, installs Vite dependencies with `npm ci`, runs the Vitest suite (`npm test -- --run`), and builds the production bundle (`npm run build`).
4. **Docker build check:** After test jobs succeed, Buildx validates the Docker images for `backend` (both `api` and `worker` targets), `ai_core`, and `web`.

## Required secrets / variables
No secrets are needed for the CI stages above. When extending the pipeline for deployments, create the following GitHub repository secrets:

| Secret | Purpose |
|--------|---------|
| `REGISTRY_USERNAME` | Container registry username (GHCR, Docker Hub, etc.). |
| `REGISTRY_TOKEN` | Token or password for pushing images. |
| `PRODUCTION_SSH_KEY` | (Optional) Key for remote docker-compose deploys. |
| `ENV_FILE_BASE64` | (Optional) Base64-encoded `.env` for remote host provisioning. |

## Extending to CD
- Add a new job depending on `docker-build` to push images (`docker/login-action`, `docker/build-push-action`) and deploy to the target host (SSH or `docker compose up` on remote).
- Use environment protection rules (`production`) so manual approvals gate production deployments.
- Store environment-specific overrides (e.g., real domain names) in GitHub Action secrets and load them with `env:` or `vars:` blocks.

## Local verification
Before pushing changes, replicate the workflow locally:
```bash
python -m pytest backend/tests
(cd backend && npm test)
(cd web && npm test -- --run && npm run build)
docker build --target api -f backend/Dockerfile .
docker build --target worker -f backend/Dockerfile .
docker build -f ai_core/Dockerfile ai_core
docker build -f web/Dockerfile web
```

With this CI scaffold in place, Phase VIII is ready for subsequent CD automation.
