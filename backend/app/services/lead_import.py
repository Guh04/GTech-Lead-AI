"""Importação de leads a partir de planilhas (.csv ou .xlsx).

O leitor é tolerante: reconhece cabeçalhos em português com variações ("Nome do negócio", "Empresa",
"WhatsApp / Telefone", "Bairro / Cidade"...), separa telefone fixo de celular, ignora duplicados e
guarda colunas sem campo correspondente (ex.: "Por que é um bom lead") nas observações do lead.
"""
import csv
import io
import re
import unicodedata
from dataclasses import dataclass, field

from pydantic import ValidationError

from app.core.errors import AppError
from app.models.enums import STATUS_LABELS, LandingStatus, LeadSource, LeadStatus
from app.schemas.lead import LeadCreate
from app.services.lead_service import LeadService

MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_ROWS = 2000
NOTES_LIMIT = 5000

# Cabeçalho normalizado -> campo do lead. "city_district" = coluna "Bairro / Cidade" (separada abaixo).
_HEADERS: dict[str, tuple[str, ...]] = {
    "company_name": ("empresa", "nome", "nome da empresa", "nome do negocio", "negocio", "razao social", "nome fantasia", "lead", "cliente"),
    "contact_name": ("responsavel", "contato", "nome do contato", "nome do responsavel", "dono", "proprietario"),
    "segment": ("segmento", "ramo", "ramo de atividade", "nicho", "categoria", "area de atuacao", "atividade"),
    "city": ("cidade", "municipio"),
    "city_district": ("bairro cidade", "cidade bairro", "bairro e cidade", "localizacao", "local", "endereco"),
    "state": ("estado", "uf"),
    "phone": ("telefone", "fone", "tel", "telefone fixo"),
    "whatsapp": ("whatsapp", "zap", "whats", "celular"),
    "phone_any": ("whatsapp telefone", "telefone whatsapp", "telefone celular", "celular telefone", "whatsapp ou telefone", "telefone whats", "contato telefonico"),
    "instagram": ("instagram", "insta", "ig", "perfil instagram"),
    "facebook": ("facebook", "face", "fb"),
    "website": ("site", "website", "site atual", "pagina web", "url", "link do site", "dominio"),
    "landing": ("landing page", "landing", "situacao da landing page", "situacao do site"),
    "status": ("status", "estagio", "etapa", "situacao", "fase"),
    "source_url": ("fonte publica", "fonte", "link da fonte", "origem do dado"),
    "do_not_contact": ("nao contatar", "nao ligar", "opt out", "optout"),
    "notes": ("observacoes", "observacao", "obs", "notas", "anotacoes", "comentarios"),
}
_FIELD_BY_HEADER = {h: f for f, hs in _HEADERS.items() for h in hs}
# Colunas que o sistema calcula sozinho ou que não fazem sentido importar.
_IGNORED = {"prioridade", "pontuacao", "score", "origem", "cadastrado em", "data encontrado", "data", "criado em", "id"}

_STATUS_WORDS = {
    "novo": "new", "novo lead": "new", "new": "new",
    "analisado": "analyzed", "analisada": "analyzed",
    "contato realizado": "contacted", "contatado": "contacted", "contactado": "contacted", "abordado": "contacted",
    "interessado": "interested", "interessada": "interested", "respondeu": "interested",
    "proposta enviada": "proposal_sent", "proposta": "proposal_sent",
    "cliente fechado": "closed_won", "fechado": "closed_won", "ganho": "closed_won", "cliente": "closed_won",
    "perdido": "lost", "perdida": "lost", "descartado": "lost",
}
_STATUS_WORDS.update({label.casefold(): s.value for s, label in STATUS_LABELS.items()})

_NO_SITE = {"nao tem", "sem site", "nao possui", "nenhum", "nao", "n a", "na", "sem", "inexistente", "none"}
_LANDING_WORDS = {
    "sem site": "none", "nao tem": "none", "none": "none",
    "site sem landing": "site_only", "tem site": "site_only", "site": "site_only",
    "com landing page": "has_landing", "com landing": "has_landing", "tem landing": "has_landing",
    "nao verificado": "unknown", "desconhecido": "unknown",
}
_YES = {"sim", "s", "yes", "y", "true", "1", "x"}


def _norm(text) -> str:
    """Minúsculas, sem acentos e sem pontuação: 'WhatsApp / Telefone' -> 'whatsapp telefone'."""
    s = unicodedata.normalize("NFKD", str(text or "")).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", s.lower())).strip()


def _cell(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        value = int(value)  # telefones numéricos do Excel chegam como 15981314488.0
    text = str(value).strip()
    # Planilhas costumam prefixar com apóstrofo para o Excel/Sheets não interpretar o texto como fórmula.
    return text[1:].strip() if text.startswith("'") else text


# ------------------------------------------------------------------ leitura do arquivo
def read_table(content: bytes, filename: str) -> tuple[list[str], list[tuple[int, list[str]]]]:
    """Devolve (cabeçalhos, [(nº da linha na planilha, células)]) de um .csv ou .xlsx; linhas vazias são puladas."""
    name = (filename or "").lower()
    if not content:
        raise AppError(422, "empty_file", "O arquivo está vazio.")
    if len(content) > MAX_FILE_BYTES:
        raise AppError(413, "file_too_large", f"Arquivo muito grande (máximo de {MAX_FILE_BYTES // 1024 // 1024} MB).")
    if name.endswith(".xlsx") or content[:2] == b"PK":
        grid = _read_xlsx(content)
    elif name.endswith((".csv", ".txt", ".tsv")) or not name.endswith((".xls", ".xlsm")):
        grid = _read_csv(content)
    else:
        raise AppError(422, "unsupported_file", "Formato não suportado. Salve a planilha como .xlsx ou .csv e tente de novo.")

    grid = [(n, row) for n, row in enumerate(grid, start=1) if any(c for c in row)]
    if len(grid) < 2:
        raise AppError(422, "empty_file", "A planilha precisa ter uma linha de cabeçalho e ao menos um lead.")
    headers, rows = grid[0][1], grid[1:]
    if len(rows) > MAX_ROWS:
        raise AppError(422, "too_many_rows", f"A planilha tem {len(rows)} linhas. Importe até {MAX_ROWS} por vez.")
    return headers, rows


def _read_csv(content: bytes) -> list[list[str]]:
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            text = content.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    first = text.split("\n", 1)[0]
    delimiter = max(",;\t", key=first.count) if any(d in first for d in ",;\t") else ","
    reader = csv.reader(io.StringIO(text, newline=""), delimiter=delimiter)
    try:
        return [[_cell(c) for c in row] for row in reader]
    except csv.Error as exc:
        raise AppError(422, "invalid_file", f"Não foi possível ler o CSV: {exc}") from exc


def _read_xlsx(content: bytes) -> list[list[str]]:
    from openpyxl import load_workbook  # import tardio: só é necessário ao importar .xlsx

    try:
        wb = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    except Exception as exc:
        raise AppError(422, "invalid_file", "Não foi possível abrir a planilha. O arquivo está corrompido ou protegido por senha?") from exc
    try:
        ws = wb.worksheets[0]
        return [[_cell(c) for c in row] for row in ws.iter_rows(values_only=True, max_row=MAX_ROWS + 50)]
    finally:
        wb.close()


# ------------------------------------------------------------------ interpretação das linhas
@dataclass
class ColumnMap:
    fields: dict[int, str] = field(default_factory=dict)  # índice da coluna -> campo
    extra: dict[int, str] = field(default_factory=dict)  # índice -> título (vai para as observações)
    ignored: list[str] = field(default_factory=list)


def map_columns(headers: list[str]) -> ColumnMap:
    cmap = ColumnMap()
    used: set[str] = set()
    for i, raw in enumerate(headers):
        key = _norm(raw)
        if not key:
            continue
        target = _FIELD_BY_HEADER.get(key)
        if target and target not in used:
            cmap.fields[i] = target
            used.add(target)
        elif key in _IGNORED:
            cmap.ignored.append(raw)
        else:
            cmap.extra[i] = raw.strip()
    return cmap


def _phones(raw_phone: str, raw_whatsapp: str, raw_any: str) -> tuple[str | None, str | None]:
    """Decide telefone e WhatsApp. Em coluna mista, celular (9 dígitos) vai para o WhatsApp."""

    def digits(value: str) -> str:
        d = re.sub(r"\D", "", value.split("/")[0].split(";")[0].split(",")[0] if value else "")
        return d[2:] if d.startswith("55") and len(d) in (12, 13) else d

    def is_mobile(d: str) -> bool:
        return len(d) == 11 and d[2] == "9"

    phone, whatsapp = digits(raw_phone) or None, digits(raw_whatsapp) or None
    mixed = digits(raw_any)
    if mixed:
        if is_mobile(mixed) and not whatsapp:
            whatsapp = mixed
        elif not phone:
            phone = mixed
    return phone, whatsapp


def _site(raw: str) -> tuple[str | None, str | None]:
    """(url, situação da landing page) a partir de 'Site atual'."""
    text = raw.strip()
    if not text:
        return None, None
    if _norm(text) in _NO_SITE:
        return None, LandingStatus.NONE.value
    if "." in text and " " not in text:
        return text, LandingStatus.SITE_ONLY.value
    return None, None


def build_payload(values: dict[str, str], extras: list[tuple[str, str]]) -> dict:
    get = lambda k: values.get(k, "").strip()  # noqa: E731

    city, district, state = get("city"), "", get("state")
    if not city and get("city_district"):
        *left, city = [p.strip() for p in get("city_district").split(",")]
        district = ", ".join(left)
    m = re.search(r"\s*[-/]\s*([A-Za-z]{2})$", city)  # "Sorocaba - SP"
    if m and not state:
        state, city = m.group(1), city[: m.start()]

    phone, whatsapp = _phones(get("phone"), get("whatsapp"), get("phone_any"))
    website, landing = _site(get("website"))
    landing_col = _LANDING_WORDS.get(_norm(get("landing")))
    status = _STATUS_WORDS.get(_norm(get("status")), LeadStatus.NEW.value)

    notes = []
    if get("notes"):
        notes.append(get("notes"))
    if district:
        notes.append(f"Bairro: {district}")
    notes += [f"{title}: {text}" for title, text in extras if text]

    payload = {
        "company_name": get("company_name"),
        "contact_name": get("contact_name") or None,
        "segment": get("segment") or None,
        "city": city or None,
        "state": state or None,
        "phone": phone,
        "whatsapp": whatsapp,
        "instagram": get("instagram") or None,
        "facebook": get("facebook") or None,
        "website": website,
        "landing_page_status": landing_col or landing or LandingStatus.UNKNOWN.value,
        "status": status,
        "source": LeadSource.IMPORT.value,
        "source_url": get("source_url") or None,
        "do_not_contact": _norm(get("do_not_contact")) in _YES,
        "notes": ("\n".join(notes)[:NOTES_LIMIT]) or None,
    }
    return payload


def _error_text(exc: ValidationError) -> str:
    labels = {"company_name": "Empresa", "phone": "Telefone", "whatsapp": "WhatsApp", "state": "Estado", "website": "Site",
              "instagram": "Instagram", "facebook": "Facebook", "source_url": "Fonte", "notes": "Observações"}
    parts = []
    for err in exc.errors():
        loc = str(err["loc"][0]) if err["loc"] else ""
        msg = str(err["msg"]).removeprefix("Value error, ")
        parts.append(f"{labels.get(loc, loc)}: {msg}" if loc else msg)
    return " ".join(parts)


def _keys(row: dict) -> list[tuple[str, str]]:
    """Chaves de duplicidade (espelham os índices únicos de database/schema.sql)."""
    keys = [("company", f"{(row.get('company_name') or '').strip().lower()}|{(row.get('city') or '').strip().lower()}")]
    for col in ("phone", "whatsapp"):
        if row.get(col):
            keys.append((col, row[col]))
    if row.get("website"):
        keys.append(("website", row["website"].lower()))
    return keys


# ------------------------------------------------------------------ importação
async def import_leads(svc: LeadService, content: bytes, filename: str, *, dry_run: bool) -> dict:
    headers, rows = read_table(content, filename)
    cmap = map_columns(headers)
    if "company_name" not in cmap.fields.values():
        raise AppError(
            422, "missing_company_column",
            "Não encontrei a coluna com o nome da empresa. Use um cabeçalho como \"Empresa\" ou \"Nome do negócio\".",
        )

    existing = await svc.db.select_all("leads", columns="company_name,city,phone,whatsapp,website")
    seen = {k for r in existing for k in _keys(r)}

    result = {
        "dry_run": dry_run, "total": len(rows), "valid": 0, "imported": 0, "duplicates": 0, "invalid": 0,
        "errors": [], "duplicate_rows": [], "preview": [],
        "columns": {"recognized": [headers[i] for i in cmap.fields], "as_notes": list(cmap.extra.values()), "ignored": cmap.ignored},
    }

    def fail(line: int, name: str, reason: str) -> None:
        result["invalid"] += 1
        if len(result["errors"]) < 50:
            result["errors"].append({"line": line, "name": name, "reason": reason})

    for n, row in rows:
        cells = row + [""] * (len(headers) - len(row))
        values: dict[str, str] = {}
        for i, target in cmap.fields.items():
            values[target] = cells[i] if i < len(cells) else ""
        extras = [(title, cells[i]) for i, title in cmap.extra.items() if i < len(cells)]
        name = values.get("company_name", "").strip()
        if not name:
            fail(n, "(sem nome)", "Empresa: informe o nome da empresa.")
            continue
        try:
            lead = LeadCreate(**build_payload(values, extras))
        except ValidationError as exc:
            fail(n, name, _error_text(exc))
            continue

        data = lead.model_dump(mode="json")
        keys = _keys(data)
        if any(k in seen for k in keys):
            result["duplicates"] += 1
            if len(result["duplicate_rows"]) < 50:
                result["duplicate_rows"].append({"line": n, "name": name})
            continue
        seen.update(keys)
        result["valid"] += 1
        if len(result["preview"]) < 5:
            result["preview"].append({k: data.get(k) for k in ("company_name", "segment", "city", "state", "phone", "whatsapp", "instagram", "website", "status")})
        if dry_run:
            continue
        try:
            await svc.create(lead)
            result["imported"] += 1
        except AppError as exc:
            result["valid"] -= 1
            if exc.status == 409:
                result["duplicates"] += 1
            else:
                fail(n, name, exc.message)
    return result
