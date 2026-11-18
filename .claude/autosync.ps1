# Commit + push automatico apos o Claude editar arquivos.
Set-Location (Split-Path -Parent $PSScriptRoot)
git add -A | Out-Null
if (git status --porcelain) {
    git commit -m ("auto: " + (Get-Date -Format "yyyy-MM-dd HH:mm")) | Out-Null
}
if (git remote) { git push -u origin HEAD 2>&1 | Out-Null }
exit 0
