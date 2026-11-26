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
    "missing": "champ obligatoire manquant",
    "extra_forbidden": "champ inconnu",
    "float_parsing": "doit être un nombre",
    "float_type": "doit être un nombre",
    "finite_number": "doit être un nombre fini",
    "string_type": "doit être un texte",
    "date_parsing": "date invalide (format attendu : AAAA-MM-JJ)",
    "date_from_datetime_parsing": "date invalide (format attendu : AAAA-MM-JJ)",
    "date_type": "date invalide (format attendu : AAAA-MM-JJ)",
    "json_invalid": "JSON invalide",
    "model_attributes_type": "le corps de la requête doit être un objet JSON",
    "dict_type": "le corps de la requête doit être un objet JSON",
}


def _french(error: dict[str, Any]) -> str:
    kind = error.get("type", "")
    ctx = error.get("ctx") or {}
    if kind == "greater_than":
        gt = ctx.get("gt")
        shown = int(gt) if isinstance(gt, float) and gt.is_integer() else gt
        return f"doit être strictement supérieur à {shown}"
    if kind == "value_error":
        # Nos propres validateurs écrivent déjà en français.
        return str(ctx.get("error", error.get("msg", ""))).removeprefix("Value error, ")
    return _MESSAGES.get(kind, error.get("msg", "valeur invalide"))


def _field(error: dict[str, Any]) -> str:
    if error.get("type") == "json_invalid":
        return "corps de la requête"
    location = [str(part) for part in error.get("loc", ()) if part != "body"]
    return ".".join(location) or "corps de la requête"


async def _validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    details = [{"field": _field(e), "message": _french(e)} for e in exc.errors()]
    message = "Requête invalide : " + " ; ".join(f"{d['field']} : {d['message']}" for d in details)
    return JSONResponse(
        status_code=422,
        content={"error": {"code": "invalid_request", "message": message, "details": details}},
    )


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(RequestValidationError, _validation_error)
