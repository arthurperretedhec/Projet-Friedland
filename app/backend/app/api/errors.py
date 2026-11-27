"""Erreurs de l'API au format commun d'architecture.md : {"error": {"code", "message", "details"}}.

Les erreurs de validation (FastAPI / pydantic) sont traduites en français, champ par champ, pour
que l'interface puisse les afficher telles quelles.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

_MESSAGES = {
    "missing": "required field missing",
    "extra_forbidden": "unknown field",
    "float_parsing": "must be a number",
    "float_type": "must be a number",
    "finite_number": "must be a finite number",
    "string_type": "must be text",
    "date_parsing": "invalid date (expected format: YYYY-MM-DD)",
    "date_from_datetime_parsing": "invalid date (expected format: YYYY-MM-DD)",
    "date_type": "invalid date (expected format: YYYY-MM-DD)",
    "json_invalid": "invalid JSON",
    "model_attributes_type": "the request body must be a JSON object",
    "dict_type": "the request body must be a JSON object",
}


def _french(error: dict[str, Any]) -> str:
    kind = error.get("type", "")
    ctx = error.get("ctx") or {}
    if kind == "greater_than":
        gt = ctx.get("gt")
        shown = int(gt) if isinstance(gt, float) and gt.is_integer() else gt
        return f"must be strictly greater than {shown}"
    if kind == "value_error":
        # Nos propres validateurs écrivent déjà en français.
        return str(ctx.get("error", error.get("msg", ""))).removeprefix("Value error, ")
    return _MESSAGES.get(kind, error.get("msg", "invalid value"))


def _field(error: dict[str, Any]) -> str:
    if error.get("type") == "json_invalid":
        return "request body"
    location = [str(part) for part in error.get("loc", ()) if part != "body"]
    return ".".join(location) or "request body"


async def _validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    details = [{"field": _field(e), "message": _french(e)} for e in exc.errors()]
    message = "Invalid request: " + "; ".join(f"{d['field']}: {d['message']}" for d in details)
    return JSONResponse(
        status_code=422,
        content={"error": {"code": "invalid_request", "message": message, "details": details}},
    )


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(RequestValidationError, _validation_error)
