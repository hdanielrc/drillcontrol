# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> See also: [AGENTS.md](AGENTS.md) for a full project overview, and [perforaciones_diamantinas/docs/](perforaciones_diamantinas/docs/) for 37+ architecture/operations guides.

---

## Commands

All commands run from `perforaciones_diamantinas/` with the virtualenv activated.

```bash
# Activate virtualenv (Windows)
venv\Scripts\activate.bat

# Dev server
python manage.py runserver

# Migrations (always makemigrations before migrate)
python manage.py makemigrations
python manage.py migrate

# Tests
python manage.py test drilling                          # full suite
python manage.py test drilling.tests.test_tareo_engine  # single module

# Static files (production)
python manage.py collectstatic
```

**Windows quick start:** `INSTALAR.bat` (one-time setup) → `INICIAR.bat` (dev server).

### Key Custom Management Commands

```bash
python manage.py sync_all_contracts             # Sync workers from Vilbragroup API
python manage.py sincronizar_consumos           # Sync supply consumption
python manage.py sincronizar_brocas_pendientes  # Sync pending drill bits
python manage.py generar_data_sistema_principal # Generate seed data
python manage.py create_superuser_with_contract # Create admin with a contract
```

---

## Architecture

Single Django app (`drilling/`) inside a Django project (`perforaciones_diamantinas/`). No frontend build pipeline — Django template engine with static CSS/JS.

### Model Organization

Models are split across three files:
- [drilling/models.py](perforaciones_diamantinas/drilling/models.py) — 57 core models in 8 labeled sections (Clientes, Personal, Maquinaria, Sondajes, Inventario, Turnos, Metas, Organigrama)
- [drilling/models_payroll.py](perforaciones_diamantinas/drilling/models_payroll.py) — 16 payroll/bonus models
- [drilling/models_tareo.py](perforaciones_diamantinas/drilling/models_tareo.py) — 4 V2 time-tracking models (`TareoPeriod`, `TareoEntry`, `TareoEntryAudit`, `TareoClosure`)

### View Separation

HTML views are split by domain; API endpoints are isolated:

| File | Domain |
|------|--------|
| `views.py` | Core (workers, machinery, shifts) |
| `views_tareo.py` | Time-tracking V1 & V2 |
| `views_payroll.py` | Payroll & bonuses |
| `views_stock.py` | Inventory |
| `views_gerencia.py` | Management dashboards |
| `views_headcount.py` | HR headcount |
| `views_organigrama.py` | Org chart |
| `views_mantenimiento.py` | Equipment maintenance |
| `views_consumo.py` | Consumption tracking |
| `api_views.py` + `api_organigrama.py` | All JSON endpoints |

Do not mix HTML and JSON responses in the same view file.

### Service Layer

Business logic lives in [drilling/utils/](perforaciones_diamantinas/drilling/utils/):
- `tareo_service.py` — time-tracking engine (V2)
- `payroll_engine.py` — bonus/salary calculations
- `stock_service.py` + `abastecimiento_service.py` — inventory logic
- `attendance_projector.py` — automatic daily projection
- `conceptos_globales_engine.py` — global metrics (PRODUCCION, CXM, SEGURIDAD)

### Multi-Tenant (Contract Scoping)

`ContractSecurityMiddleware` enforces that each user sees only their own contract's data. Every queryset must filter by `request.contrato`. Forgetting this causes cross-tenant data leakage. Supported contract types: `DDH`, `SGEOL`, `WDTH`, `VCR`.

### Role-Based Access

`RoleBasedTemplateMiddleware` assigns role-specific base templates. Seven roles: `GERENCIA`, `CONTROL_PROYECTOS`, `ADMINISTRADOR`, `RESIDENTE`, `LOGISTICO`, `OPERADOR`, `TRABAJADOR`. Use helpers in [mixins.py](perforaciones_diamantinas/drilling/mixins.py) for permission checks — avoid inline role checks.

### Tareo V1 vs V2

Two coexisting time-tracking systems:
- **V1 (legacy):** uses `Asistencia` model, `views_tareo.py` basic views — do not add features here.
- **V2 (current):** normalized schema, auto-projection. Uses `AsistenciaTrabajador` / `TurnoTrabajador`. All new time-tracking work targets V2.

### External API Integration

[drilling/api_client.py](perforaciones_diamantinas/drilling/api_client.py) uses `cloudscraper` to bypass Cloudflare on the Vilbragroup TIC API. Syncs workers, consumables, and drill bits. Base URL is in `.env` (`API_VILBRAGROUP_BASE_URL`).

---

## Conventions

- **Language:** All model fields, view names, variable names, and comments are in **Spanish**. Maintain this in new code.
- **New models:** Follow the `is_active` / `fecha_creacion` / `fecha_modificacion` pattern. Add to the appropriate section in `models.py` or a new `models_<feature>.py`.
- **Migrations:** 104+ migrations exist — always check for conflicts before creating new ones.
- **Config:** Database credentials and secrets come from `.env` (never hardcoded). Use `.env.production` as a reference template.
- **Performance:** Use `annotate()` + `F()` + `Sum()` for aggregates on dashboards; avoid per-row queries. The middleware caches contract/role lookups — don't bypass it with extra DB hits.

# Django Project

> Claude Code configuration for Django projects with HTMX and modern Python tooling.

## Quick Facts

- **Stack**: Django, PostgreSQL, HTMX
- **Package Manager**: uv
- **Test Command**: `uv run pytest`
- **Lint Command**: `uv run ruff check .`
- **Format Command**: `uv run ruff format .`
- **Type Check**: `uv run pyright`

## Key Directories

- `apps/` - Django applications
- `config/` - Django settings and root URLconf
- `templates/` - Django/Jinja2 templates
- `static/` - CSS, JavaScript, images
- `tests/` - Test files
- `tasks/` - Celery tasks

## Code Style

- Python 3.12+ with type hints required
- Ruff for linting and formatting (replaces black, isort, flake8)
- pyright strict mode enabled
- No `Any` types - use proper type hints or `object`
- Use early returns, avoid nested conditionals
- Prefer composition over inheritance

## Git Conventions

- **Branch naming**: `{initials}/{description}` (e.g., `jd/fix-login`)
- **Commit format**: Conventional Commits (`feat:`, `fix:`, `docs:`, etc.)
- **PR titles**: Same as commit format

## Critical Rules

### Error Handling
- NEVER swallow errors silently
- Always show user feedback for errors (Django messages, HTMX response headers)
- Log errors with proper context for debugging

### Views
- Prefer Function-Based Views
- Always validate request.method explicitly
- Return proper HTTP status codes
- Use `select_related()` / `prefetch_related()` to avoid N+1 queries

### Templates & HTMX
- Use template inheritance (`{% extends %}`, `{% block %}`)
- Create partial templates for HTMX responses (`_partial.html` naming)
- Always include `hx-indicator` for loading states
- Handle `HX-Request` header for partial vs full page responses

### Forms
- Use ModelForm for model-backed forms
- Validate in `clean()` and `clean_<field>()` methods
- Always handle form errors in templates
- Disable submit buttons during HTMX requests

### Celery Tasks
- Tasks must be idempotent
- Use proper retry strategies with exponential backoff
- Always log task start/completion/failure
- Pass serializable arguments only (no model instances)

## Testing

- Write failing test first (TDD)
- Use Factory Boy: `UserFactory.create(is_admin=True)`
- Use pytest fixtures in `conftest.py`
- Test behavior, not implementation
- Run tests before committing

## Skill Activation

Before implementing ANY task, check if relevant skills apply:

- Debugging issues → `systematic-debugging` skill
- Exploring Django project (models, URLs, settings) → `django-extensions` skill
- Creating new skills → `skill-creator` skill
- Starting a new task → `onboard` skill
- Working a ticket → `ticket` skill
- Reviewing a PR → `pr-review` skill
- Summarizing branch changes → `pr-summary` skill
- Running quality checks → `code-quality` skill
- Checking docs accuracy → `docs-sync` skill
- Committing worktree changes and merging to master/main → `worktree-commit-merge` skill

## Common Commands

```bash
# Development
uv run python manage.py runserver     # Start dev server
uv run pytest                         # Run tests
uv run pytest -x --lf                 # Run last failed, stop on first failure
uv run ruff check .                   # Lint code
uv run ruff format .                  # Format code
uv run pyright                        # Type check

# Django
uv run python manage.py makemigrations
uv run python manage.py migrate
uv run python manage.py shell_plus    # Enhanced shell (django-extensions)
uv run python manage.py createsuperuser

# Celery
uv run celery -A config worker -l info
uv run celery -A config beat -l info

# Dependencies
uv sync                               # Install from pyproject.toml
uv add <package>                      # Add new dependency
uv add --dev <package>                # Add dev dependency

# Git
gh pr create                          # Create PR
```