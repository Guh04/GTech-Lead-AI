# GTech Lead AI

Painel web de gerenciamento e prospecção de leads comerciais (FastAPI + Supabase + HTML/CSS/JS puro).

Documentação completa, com instalação, configuração do Supabase, execução local e publicação: **[docs/README.md](docs/README.md)**.

Início rápido (Windows PowerShell):

```powershell
cd backend
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env      # preencha SUPABASE_URL e SUPABASE_ANON_KEY
uvicorn app.main:app --reload
```

Depois abra http://localhost:8000.
