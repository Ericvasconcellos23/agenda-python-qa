$ErrorActionPreference = "Stop"

# Recupera a credencial protegida pelo Windows.
$credencialAgenda = Import-Clixml "$env:LOCALAPPDATA\AgendaPython\gmail.xml"

# Configura o envio de e-mails para este processo.
$env:EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
$env:EMAIL_HOST = "smtp.gmail.com"
$env:EMAIL_PORT = "587"
$env:EMAIL_HOST_USER = $credencialAgenda.UserName
$env:DEFAULT_FROM_EMAIL = $credencialAgenda.UserName
$env:EMAIL_HOST_PASSWORD = $credencialAgenda.GetNetworkCredential().Password

# Executa os lembretes na pasta onde este arquivo está salvo.
Push-Location $PSScriptRoot
try {
    & "$PSScriptRoot\.venv\Scripts\python.exe" manage.py process_reminders --loop
}
finally {
    Remove-Item Env:\EMAIL_HOST_PASSWORD -ErrorAction SilentlyContinue
    Pop-Location
}