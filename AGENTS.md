# DrillControl — Agent Instructions

**DrillControl** is a Django 5.0.7 web application for managing diamond drilling operations (perforaciones diamantinas): workers, machinery, drilling shifts, payroll, time-tracking (tareo), inventory, and project management. It integrates with an external Vilbragroup API for syncing worker data.

---

## Project Layout

```
drillcontrol/
├── AGENTS.md                            # This file
├── INICIAR.bat / INSTALAR.bat           # Windows helper scripts
├── perforaciones_diamantinas/           # Django project root
│   ├── manage.py
│   ├── requirements.txt
│   ├── perforaciones_diamantinas/       # Django config module (settings, urls, wsgi)
│   ├── drilling/                        # Main (and only) Django app
│   │   ├── models.py                    # Core models (8 sections)
│   │   ├── models_payroll.py            # Payroll & bonus models
│   │   ├── models_tareo.py              # Time-tracking V2 models
│   │   ├── views.py                     # HTML views (core)
│   │   ├── views_tareo.py               # Tareo V1 & V2 HTML views
│   │   ├── views_stock.py               # Inventory views
│   │   ├── views_payroll.py             # Payroll views
│   │   ├── views_gerencia.py            # Management dashboard
│   │   ├── views_headcount.py           # HR headcount
│   │   ├── views_gestion_proyectos.py   # Project management
│   │   ├── views_organigrama.py         # Org chart
│   │   ├── views_mantenimiento.py       # Equipment maintenance
│   │   ├── views_consumo.py             # Consumption tracking
│   │   ├── api_views.py                 # JSON API endpoints
│   │   ├── api_organigrama.py           # Org chart API
│   │   ├── api_client.py                # Vilbragroup external API client
│   │   ├── auth_views.py                # Login, password reset
│   │   ├── middleware.py                # ContractSecurityMiddleware, RoleBasedTemplateMiddleware
│   │   ├── management/commands/         # Custom `manage.py` commands (~20 commands)
│   │   ├── migrations/                  # 104+ migration files
│   │   ├── utils/                       # Utility functions
│   │   ├── templatetags/                # Custom template tags
│   │   └── tests/                       # Unit & integration tests
│   ├── docs/                            # 37+ markdown docs (architecture, guides, etc.)
│   ├── plantillas/                      # Excel templates
│   └── sql_views/                       # SQL views for Power BI reporting
└── scripts/                             # Root-level maintenance scripts
```

---

## Dev Setup & Common Commands

All commands run from `perforaciones_diamantinas/` with the virtualenv activated.

```bash
# Activate venv (Windows)
venv\Scripts\activate.bat

# Run dev server
python manage.py runserver

# Migrations
python manage.py makemigrations
python manage.py migrate

# Tests
python manage.py test

# Collect static (production)
python manage.py collectstatic
```

### Key Custom Management Commands

```bash
python manage.py sync_all_contracts           # Sync workers from Vilbragroup API
python manage.py sincronizar_consumos         # Sync supply consumption data
python manage.py sincronizar_brocas_pendientes  # Sync pending drill bits
python manage.py generar_data_sistema_principal # Generate seed/demo data
python manage.py create_superuser_with_contract # Create admin with contract
```

### Windows Quick Start

```cmd
INSTALAR.bat   # One-time setup: creates venv, installs deps, runs migrations
INICIAR.bat    # Start development server at http://localhost:8000
```

---

## Architecture & Conventions

### Language
All model fields, view names, docstrings, comments, and variable names are in **Spanish**. Keep this convention when adding new code.

### View Separation Pattern
HTML views are split by domain into `views_*.py` files. JSON/API endpoints live in `api_views.py` and `api_organigrama.py`. Do **not** mix HTML and JSON responses in the same view file.

### Multi-Tenant / Multi-Contract
The app supports multiple service contracts (DDH, SGEOL, WDTH, VCR). `ContractSecurityMiddleware` enforces contract scoping. Views should always filter querysets by the active contract from `request.contrato`.

### Role-Based Access
`RoleBasedTemplateMiddleware` assigns templates based on user role. Roles: `gerente`, `supervisor`, `trabajador`. Use `mixins.py` helpers for role checks rather than inline permission checks.

### Model Conventions
- Models in `models.py` are organized into 8 labeled sections with comments.
- Use existing base patterns: `is_active` boolean flag, `fecha_creacion`/`fecha_modificacion` timestamps.
- New models should be added in the appropriate section or a new `models_<feature>.py` file.

### Tareo (Time-Tracking)
Two systems coexist:
- **V1 (legacy)**: `views_tareo.py` (basic), uses `Asistencia` model.
- **V2 (current)**: normalized, with auto-projection. Uses `AsistenciaTrabajador`, `TurnoTrabajador`. Prefer V2 for new features.

---

## Database

- **PostgreSQL** with `django-db-connection-pool` (10 base + 10 overflow connections).
- Configuration via `.env` file (copy `.env.production` as a reference).
- Production host: `138.197.203.247`, DB: `drilldb`.
- Never hardcode credentials — always use `environ` / `os.getenv`.

---

## Key Documentation

| Topic | File |
|-------|------|
| Installation guide | [GUIA_INSTALACION.md](GUIA_INSTALACION.md) |
| Deployment (prod) | [docs/DESPLIEGUE.md](perforaciones_diamantinas/docs/DESPLIEGUE.md) |
| Tareo V2 architecture | [docs/README_TAREO_V2.md](perforaciones_diamantinas/docs/README_TAREO_V2.md) |
| Tareo V2 migration | [docs/MIGRACION_TAREO_V2.md](perforaciones_diamantinas/docs/MIGRACION_TAREO_V2.md) |
| Payroll & bonuses | [docs/GUIA_HORAS_EXTRAS.md](perforaciones_diamantinas/docs/GUIA_HORAS_EXTRAS.md) |
| Multi-contract access | [docs/ACCESO_MULTI_CONTRATO.md](perforaciones_diamantinas/docs/ACCESO_MULTI_CONTRATO.md) |
| Sync guides | [docs/GUIA_SINCRONIZACION.md](perforaciones_diamantinas/docs/GUIA_SINCRONIZACION.md) |
| Drill bit history | [docs/README_HISTORIAL_BROCAS.md](perforaciones_diamantinas/docs/README_HISTORIAL_BROCAS.md) |
| Production changes summary | [docs/RESUMEN_CAMBIOS.md](perforaciones_diamantinas/docs/RESUMEN_CAMBIOS.md) |

---

## Common Pitfalls

- **Migrations**: Always run `makemigrations` before `migrate` after model changes. The project has 104+ migrations — check for conflicts before creating new ones.
- **Contract scoping**: Forgetting to filter by `contrato` in queries leads to data leakage across tenants.
- **Static files**: Run `collectstatic` after adding new CSS/JS in `static/drilling/`.
- **`.env` file**: The server expects a `.env` file in `perforaciones_diamantinas/`. Use `.env.production` as reference.
- **Tareo V1 vs V2**: Do not add features to V1 views — new development targets V2.
