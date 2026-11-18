from pydantic import BaseModel, ConfigDict, Field, field_validator

MAX_BODY = 1000


class GenerateRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    count: int = Field(10, ge=1, le=100)
    search_id: str | None = None  # restringe aos leads de uma pesquisa de prospecção

    @field_validator("search_id")
    @classmethod
    def _uuid(cls, v):
        if v is None:
            return v
        import uuid

        try:
            return str(uuid.UUID(str(v)))
        except ValueError as exc:
            raise ValueError("Identificador da pesquisa inválido.") from exc


class MessageUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    body: str

    @field_validator("body", mode="before")
    @classmethod
    def _body(cls, v):
        text = str(v or "").strip()
        if not text:
            raise ValueError("A mensagem não pode ficar vazia.")
        if len(text) > MAX_BODY:
            raise ValueError(f"Mensagem muito longa (máximo de {MAX_BODY} caracteres).")
        return text


class OutreachStatusOut(BaseModel):
    daily_limit: int
    sent_today: int
    remaining: int
    min_interval_seconds: int
    wait_seconds: int  # tempo até o próximo envio liberado (0 = pode enviar agora)
    ai_configured: bool
