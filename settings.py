"""
settings.py (project root) — compatibility shim.

This project used to have two independent settings modules (one here at the
root, one at backend/config.py) from two different branches. Only
backend/config.py ever made it into `main`, so anything doing
`from settings import settings` (backend/main.py, backend/llm/groq_client.py)
was crashing with `ModuleNotFoundError: No module named 'settings'`.

backend/config.py is now the single source of truth for all configuration.
This file just re-exports it so existing imports keep working without
having to touch every call site. New code should prefer:

    from backend.config import settings
"""
from backend.config import settings  # noqa: F401