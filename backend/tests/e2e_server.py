"""Servidor para testes ponta a ponta no navegador (NÃO usar em produção).

Sobe a aplicação real (frontend + API) apontando para um Supabase FALSO em memória,
com um usuário de teste. Uso:
    python -m tests.e2e_server            # porta 8765
Usuário: teste@gtech.com / senha-teste
"""
import sys

import uvicorn

from app.main import create_app
from tests.conftest import make_settings
from tests.fake_supabase import FakeSupabase

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8765

fake = FakeSupabase()
fake.add_user("teste@gtech.com", "senha-teste")
app = create_app(make_settings(), http_client=fake.client())

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="warning")
