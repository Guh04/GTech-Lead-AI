"""Autenticação, mensagens de erro e comportamento sem/ com falha do Supabase."""
import httpx


def test_health_reports_configuration(client, make_client):
    assert client.get("/api/health").json()["supabase_configured"] is True
    unconfigured = make_client(supabase_url="", supabase_anon_key="")
    body = unconfigured.get("/api/health").json()
    assert body["supabase_configured"] is False
    assert "SUPABASE_URL" in body["message"]


def test_api_returns_clear_message_when_supabase_not_configured(make_client):
    c = make_client(supabase_url="", supabase_anon_key="")
    r = c.get("/api/leads", headers={"Authorization": "Bearer x"})
    assert r.status_code == 503
    assert r.json()["error"]["code"] == "supabase_not_configured"
    assert c.post("/api/auth/login", json={"email": "a@b.com", "password": "x"}).status_code == 503


def test_login_success_and_wrong_password(client):
    ok = client.post("/api/auth/login", json={"email": "ana@teste.com", "password": "senha-segura"})
    assert ok.status_code == 200
    body = ok.json()
    assert body["access_token"] and body["refresh_token"] and body["user"]["email"] == "ana@teste.com"

    bad = client.post("/api/auth/login", json={"email": "ana@teste.com", "password": "errada"})
    assert bad.status_code == 401
    assert bad.json()["error"]["message"] == "E-mail ou senha incorretos."


def test_protected_routes_require_token(client):
    for method, path in [("get", "/api/leads"), ("get", "/api/dashboard"), ("get", "/api/me"), ("get", "/api/reports")]:
        r = getattr(client, method)(path)
        assert r.status_code == 401, path
        assert r.json()["error"]["code"] == "not_authenticated"
    r = client.get("/api/leads", headers={"Authorization": "Bearer token-invalido"})
    assert r.status_code == 401
    assert "expirou" in r.json()["error"]["message"]


def test_me_and_token_verification_is_cached(client, ana, fake):
    assert client.get("/api/me", headers=ana).json()["email"] == "ana@teste.com"
    client.get("/api/leads", headers=ana)
    client.get("/api/dashboard", headers=ana)
    assert fake.auth_calls == 1  # só uma validação no Supabase Auth para várias requisições


def test_refresh_and_logout(client, fake):
    session = client.post("/api/auth/login", json={"email": "ana@teste.com", "password": "senha-segura"}).json()
    new = client.post("/api/auth/refresh", json={"refresh_token": session["refresh_token"]})
    assert new.status_code == 200 and new.json()["access_token"] != session["access_token"]
    # refresh token já usado
    again = client.post("/api/auth/refresh", json={"refresh_token": session["refresh_token"]})
    assert again.status_code == 401

    headers = {"Authorization": f"Bearer {new.json()['access_token']}"}
    assert client.get("/api/me", headers=headers).status_code == 200
    assert client.post("/api/auth/logout", headers=headers).status_code == 204
    assert client.get("/api/me", headers=headers).status_code == 401


def test_supabase_unreachable_gives_friendly_503(client, ana, fake):
    client.get("/api/me", headers=ana)  # aquece o cache de autenticação
    fake.fail_with = httpx.ConnectError("sem rede")
    r = client.get("/api/leads", headers=ana)
    assert r.status_code == 503
    assert r.json()["error"]["code"] == "supabase_unreachable"
    assert "conectar ao Supabase" in r.json()["error"]["message"]


def test_missing_tables_points_to_sql_files(client, ana, fake):
    fake.missing_tables = True
    r = client.get("/api/leads", headers=ana)
    assert r.status_code == 503
    assert r.json()["error"]["code"] == "database_not_ready"
    assert "schema.sql" in r.json()["error"]["message"]


def test_session_revoked_mid_session_returns_401(client, ana, fake):
    assert client.get("/api/leads", headers=ana).status_code == 200
    fake.tokens.clear()
    client.app.state.auth._cache.clear()
    assert client.get("/api/leads", headers=ana).status_code == 401


def test_validation_errors_are_in_portuguese_with_field(client, ana):
    r = client.post("/api/leads", json={"company_name": ""}, headers=ana)
    assert r.status_code == 422
    err = r.json()["error"]
    assert err["code"] == "validation_error"
    assert err["details"][0]["field"] == "company_name"
    assert "nome da empresa" in err["details"][0]["message"].lower()

    r = client.post("/api/leads", json={}, headers=ana)
    assert r.json()["error"]["details"][0]["message"] == "Campo obrigatório."


def test_unknown_routes_and_security_headers(client):
    r = client.get("/api/nao-existe")
    assert r.status_code == 404 and r.json()["error"]["message"]
    page = client.get("/")
    assert page.status_code == 200
    assert page.headers["x-content-type-options"] == "nosniff"
    assert "default-src 'self'" in page.headers["content-security-policy"]
    assert client.get("/api/health").headers["cache-control"] == "no-store"


def test_production_hides_docs(make_client):
    assert make_client(app_env="production").get("/docs").status_code == 404
    assert make_client(app_env="development").get("/docs").status_code == 200


def test_no_secret_keys_exposed(client):
    """O frontend nunca recebe chaves do Supabase."""
    for path in ["/api/health", "/", "/js/app.js", "/js/api.js"]:
        body = client.get(path).text
        assert "anon-key-for-tests" not in body
        assert "service_role" not in body


def test_unexpected_error_does_not_leak_details(make_client, monkeypatch):
    from app.services import lead_service

    async def boom(*a, **k):
        raise RuntimeError("segredo interno")

    monkeypatch.setattr(lead_service.LeadService, "facets", boom)
    c = make_client(raise_server_exceptions=False)
    token = c.post("/api/auth/login", json={"email": "ana@teste.com", "password": "senha-segura"}).json()["access_token"]
    r = c.get("/api/leads/facets", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 500
    assert "segredo interno" not in r.text
    assert r.json()["error"]["code"] == "internal_error"


def test_rls_violation_has_specific_message(client, ana, fake, monkeypatch):
    original = fake._rest

    def deny(request, url):
        if request.method == "POST":
            return httpx.Response(403, json={"code": "42501", "message": 'new row violates row-level security policy for table "leads"'})
        return original(request, url)

    monkeypatch.setattr(fake, "_rest", deny)
    r = client.post("/api/leads", json={"company_name": "Clínica X", "city": "Campinas", "state": "SP", "phone": "19999990000"}, headers=ana)
    assert r.status_code == 503 and r.json()["error"]["code"] == "database_policy_missing"
    assert '"leads"' in r.json()["error"]["message"] and "policies.sql" in r.json()["error"]["message"]
