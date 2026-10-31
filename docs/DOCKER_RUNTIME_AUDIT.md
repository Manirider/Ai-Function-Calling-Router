# Docker Runtime Audit

## Environment
docker --version: Docker version 29.5.3, build d1c06ef
docker compose version: Docker Compose version v5.1.4
docker info: Server connection failed: npipe:////./pipe/dockerDesktopLinuxEngine not found
=> Docker daemon not running. Runtime verification BLOCKED.

## Files Inspected
Dockerfile, docker-compose.yml, requirements.txt, .env.example, evaluate_router.py, src/, data/, .dockerignore

## Findings - Pre-modification
- Dockerfile used python:3.11-slim, stable base.
- WORKDIR /app set correctly.
- Dependencies installed from requirements.txt.
- src, data, evaluate_router.py copied into image.
- .env.example copied to .env unnecessarily; PROVIDER_MODE=offline enforced via ENV.
- Output directory created with chmod 777.
- docker-compose.yml builds from repo root, mounts ./output to /app/output, sets PROVIDER_MODE=offline, OUTPUT_DIR=output.
- No secrets committed.
- No external network required at runtime.
- No .dockerignore present initially.
- Container ran as root.

## Remediation Applied
- Dockerfile:
  - Removed unnecessary COPY .env.example .env
  - Added non-root user appuser uid 1000
  - Chown /app to appuser and set output directory world-writable
  - USER appuser before CMD
  - Maintains ENV PROVIDER_MODE=offline and OUTPUT_DIR=output
  - CMD ["python", "evaluate_router.py"] unchanged
- docker-compose.yml:
  - Explicit build context and dockerfile specification
  - Added explicit command: python evaluate_router.py for clear exit code propagation
  - Volume mount ./output:/app/output preserved
  - Environment variables preserved
- Created .dockerignore to exclude .git, __pycache__, .pytest_cache, .env, venv, tests, docs, results, output/* from build context

## Post-modification Verification
- docker compose config validates successfully.
- Build context size reduced via .dockerignore.
- No secrets or virtual environments copied.
- Module paths remain valid: src/, data/ present.
- Deterministic offline provider remains default via ENV.
- No external API key required.

## Known Limitations
- Docker daemon unavailable in current environment; runtime execution BLOCKED.
- Volume mount permissions depend on host filesystem; output directory set world-writable to mitigate.
- Non-root user may conflict with host UID mapping on some Linux hosts; chmod 777 provides fallback.

## Commands to verify on Docker-enabled machine
docker compose config
docker compose build --no-cache
docker compose run --rm evaluator
Verify host output/metrics.json exists, parses, contains baseline and recovery_active keys with completion_rate, silent_wrong_rate, mean_recovery_attempts
Verify output/dataset_coverage.json, per_case_results.jsonl, recovery_breakdown.json, evaluation_report.json present

## Status
Build config VALID after remediation. Runtime BLOCKED due to daemon not running.
