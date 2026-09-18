# Rule 01: Code Style, Formatting, and Typing

## Linter & Formatter
- **Ruff** is the sole linter and formatter.
- Check formatting and lint rules before any commit:
  ```bash
  ruff check .
  ruff format --check .
  ```
- Line length is pinned to 100 characters.

## Typing & Contracts
- Every function and method in `src/traceai/pipelines/`, `src/traceai/core/`, and `src/traceai/db/` must have complete type annotations.
- Numerical arrays and embeddings must be typed explicitly (e.g., `np.ndarray`, `list[float]`).
- Do not use `Any` where a Union, TypeVar, or specific Pydantic model can be specified.

## Boundaries
- Pydantic models (`BaseModel`) are required at all entry points:
  - FastAPI request and response payloads.
  - Celery / Async queue messages.
  - Lineage and certificate representations.
- Never pass unvalidated dictionaries across module boundaries.
