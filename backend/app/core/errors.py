"""Erros da aplicação e tratadores globais.

Todas as respostas de erro seguem o formato:
    {"error": {"code": "...", "message": "mensagem compreensível", "details": [...] | null}}
"""
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger("gtech")


class AppError(Exception):
    def __init__(self, status: int, code: str, message: str, details: list[dict] | None = None):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.details = details


def not_found(what: str = "Registro") -> AppError:
    return AppError(404, "not_found", f"{what} não encontrado.")


def error_body(code: str, message: str, details: list[dict] | None = None) -> dict:
    return {"error": {"code": code, "message": message, "details": details}}


# --- tradução das mensagens de validação do Pydantic --------------------------
_FRIENDLY = {
    "missing": "Campo obrigatório.",
    "string_too_short": "Texto muito curto.",
    "string_type": "Informe um texto válido.",
    "int_parsing": "Informe um número inteiro válido.",
    "int_type": "Informe um número inteiro válido.",
    "bool_parsing": "Valor inválido.",
    "enum": "Valor não permitido.",
    "literal_error": "Valor não permitido.",
    "uuid_parsing": "Identificador inválido.",
    "uuid_type": "Identificador inválido.",
    "too_short": "Lista muito curta.",
    "too_long": "Lista muito longa.",
    "json_invalid": "JSON inválido.",
}


def _friendly_message(err: dict) -> str:
    kind = err.get("type", "")
    ctx = err.get("ctx") or {}
    if kind == "value_error":
        return str(err.get("msg", "Valor inválido.")).removeprefix("Value error, ")
    if kind == "string_too_long":
        return f"Texto muito longo (máximo de {ctx.get('max_length')} caracteres)."
    if kind in {"greater_than_equal", "less_than_equal", "greater_than", "less_than"}:
        return "Valor fora do intervalo permitido."
    if kind == "too_short":
        return "Informe ao menos um item."
    return _FRIENDLY.get(kind, str(err.get("msg", "Valor inválido.")))


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError):
        return JSONResponse(error_body(exc.code, exc.message, exc.details), status_code=exc.status)

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError):
        details = []
        for err in exc.errors():
            loc = [str(p) for p in err.get("loc", ()) if p not in ("body", "query", "path")]
            details.append({"field": ".".join(loc) or "body", "message": _friendly_message(err)})
        message = "Dados inválidos. " + (details[0]["message"] if len(details) == 1 else "Corrija os campos destacados.")
        return JSONResponse(error_body("validation_error", message, details), status_code=422)

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException):
        messages = {404: "Recurso não encontrado.", 405: "Método não permitido.", 401: "Não autenticado."}
        message = messages.get(exc.status_code, str(exc.detail))
        return JSONResponse(error_body("http_error", message), status_code=exc.status_code)

    @app.exception_handler(Exception)
    async def _unexpected(_: Request, exc: Exception):
        log.exception("Erro inesperado: %s", exc)
        return JSONResponse(
            error_body("internal_error", "Ocorreu um erro interno. Tente novamente em instantes."),
            status_code=500,
        )
