# Funcionar com o computador desligado

Arquitetura: navegador → servidor Django → SQLite persistente; um worker separado consulta o mesmo banco e cria mensagens/envia e-mails pelo SMTP. Não há serviço de IA nessa arquitetura.

Esta entrega não cria conta de hospedagem nem configura SMTP real. Não é possível confirmar envio externo ou funcionamento contínuo antes dessas etapas. Não foi selecionado um plano gratuito: limites e preços precisam ser verificados no momento da contratação.

## Requisitos da hospedagem

Python 3.12; HTTPS; processo web contínuo; um único worker contínuo ou agendador que rode a cada minuto; volume persistente compartilhado entre web e worker; backup do SQLite; variáveis secretas; reinício automático e monitoramento. Plataformas que suspendem processos ou apagam disco local não atendem esta arquitetura. Se web e worker estiverem em máquinas diferentes, migre para PostgreSQL em vez de SQLite compartilhado pela rede.

## Comandos de implantação (Linux)

```bash
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py check --deploy
# Processo web, atrás de HTTPS:
gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 1
# Outro processo, mesma configuração e banco:
python manage.py process_reminders --loop
```

`check --deploy` detecta parte dos erros de configuração; resolva avisos pertinentes. Configure `DEBUG=0`, chave aleatória, hosts, origens HTTPS e caminho persistente do banco. `.env.example` é uma referência: configure variáveis na plataforma. Não é carregado automaticamente. Para proxy que termina TLS, configure `SECURE_PROXY_SSL_HEADER` apenas depois de confirmar que o proxy remove cabeçalhos enviados pelo cliente e define o cabeçalho confiável; uma configuração errada pode causar redirecionamento contínuo ou enfraquecer HTTPS.

## E-mail

Selecione um provedor com SMTP compatível com TLS na porta 587. Confira limites do plano, verificação de domínio/remetente e condições atuais. Defina `EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend` e as outras variáveis do exemplo. Credenciais devem ficar fora do código e do Git. Faça teste real com seu endereço. Não basta um teste com mock para confirmar entrega externa.

## Antes de cadastro público

Adicionar limitação de tentativas de login/cadastro, verificação de e-mail, recuperação de senha, política de privacidade e mecanismos para exclusão de conta. Validar prevenção de duplicidade de cadastro em concorrência; a primeira versão usa o username único e checagem no formulário, mas uma corrida pode retornar erro de banco. Configurar alertas de worker parado, backups/restauração, atualização de dependências e validação de SMTP. Para vários workers, usar fila/outbox e coordenação transacional. Estes itens são evolução posterior, não funcionalidades já implementadas.

## Operação sem IA

Guardar código no Git e credenciais no provedor; manter web e worker supervisionados; acompanhar falhas; rodar CI a cada mudança; atualizar dependências com testes; testar restauração de backups. O aplicativo continua funcionando sem ChatGPT. Serviços de hospedagem, banco e SMTP precisam continuar disponíveis.

Referência: https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/
