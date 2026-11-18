import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from tests.fake_supabase import ANON_KEY, SUPABASE_URL, FakeSupabase


def make_settings(**overrides) -> Settings:
    base = dict(
        supabase_url=SUPABASE_URL, supabase_anon_key=ANON_KEY, app_env="development", app_timezone="America/Sao_Paulo",
        cors_origins="", prospecting_api_url="", prospecting_api_key="", prospecting_timeout_seconds=5, osm_enabled=False, osm_retry_delay_seconds=0,
    )
    # _env_file=None: os testes nunca leem o backend/.env real do usuário
    return Settings(_env_file=None, **{**base, **overrides})


@pytest.fixture
def fake() -> FakeSupabase:
    f = FakeSupabase()
    f.add_user("ana@teste.com")
    f.add_user("bia@teste.com")
    return f


@pytest.fixture
def make_client(fake):
    clients = []

    def _make(raise_server_exceptions: bool = True, **settings_overrides) -> TestClient:
        app = create_app(make_settings(**settings_overrides), http_client=fake.client())
        c = TestClient(app, raise_server_exceptions=raise_server_exceptions)
        c.__enter__()
        clients.append(c)
        return c

    yield _make
    for c in clients:
        c.__exit__(None, None, None)


@pytest.fixture
def client(make_client) -> TestClient:
    return make_client()


@pytest.fixture
def ana(fake) -> dict:
    return {"Authorization": f"Bearer {fake.login('ana@teste.com')}"}


@pytest.fixture
def bia(fake) -> dict:
    return {"Authorization": f"Bearer {fake.login('bia@teste.com')}"}


def lead(**kw) -> dict:
    """Payload mínimo de lead para os testes."""
    return {"company_name": "Clínica Sorriso", "city": "Campinas", "state": "SP", **kw}
