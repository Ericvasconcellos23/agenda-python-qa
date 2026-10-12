# Minha Agenda — Python e QA

Aplicativo web responsivo de lembretes, com Django, SQLite, HTML/CSS e testes automatizados. Funciona pelo navegador do computador ou telefone. Não usa IA em sua execução. Primeira versão de estudo, ainda não hospedada.

## Começar no Windows (PowerShell)

Instale Python 3.12 e extraia este projeto. Abra o terminal dentro da pasta `agenda`:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver
```

Abra http://127.0.0.1:8000, clique em **Criar conta**, cadastre seu nome, e-mail e senha. Depois entre usando o e-mail em letras minúsculas. Cadastre uma atividade para daqui a dois minutos.

Em OUTRO terminal, na mesma pasta, inicie o processo de lembretes:

```powershell
.\.venv\Scripts\python.exe manage.py process_reminders --loop
```

Ele verifica os horários a cada 30 segundos. Atualize a página após o horário para ver a notificação. Em desenvolvimento, o e-mail é impresso nesse segundo terminal: nenhum e-mail real é enviado por padrão. Encerre os processos com Ctrl+C.

Linux/macOS: use `python3 -m venv .venv` e substitua `.\.venv\Scripts\python.exe` por `.venv/bin/python`.

## Testes automatizados

```powershell
.\.venv\Scripts\python.exe -m coverage run --source=lembretes manage.py test -v 2
.\.venv\Scripts\python.exe -m coverage report
.\.venv\Scripts\python.exe -m coverage html
```

O banco de testes é temporário e separado do banco da aplicação. Veja `docs/resultado-testes.txt` para a execução feita nesta entrega. O workflow em `.github/workflows/tests.yml` repete os testes em pushes e pull requests quando você publicar o projeto no GitHub. Execute também `python manage.py makemigrations --check --dry-run` para detectar migrações esquecidas.

## Ler e aprender

1. `docs/GUIA-CODIGO.md`: explicação de cada módulo e dos blocos principais.
2. `docs/PLANO-QA.md`: critérios de aceitação, cenários manuais, riscos e exemplo de bug.
3. `docs/NUVEM.md`: arquitetura e requisitos para funcionamento com seu computador desligado.

## O que a primeira versão faz

Cadastro com nome, e-mail único e senha com hash; login/logout; criar, editar, concluir e excluir atividades; mensagens persistidas no app e marcação como lidas; envio SMTP configurável; novas tentativas de e-mail; validação de data futura; horários de São Paulo; proteção CSRF e filtragem por usuário.

## Limites conhecidos

A mensagem aparece ao abrir/atualizar a página. Não há push no celular com o app fechado. O e-mail depende de provedor SMTP, conectividade e limites da conta. Aceitação pelo SMTP não garante chegada na caixa de entrada. Um worker verifica a cada 30 segundos; não há garantia de entrega no segundo exato. Sem recorrência, recuperação de senha, confirmação de e-mail ou limitação de tentativas de login nesta versão. Não publique o cadastro na internet antes de tratar os controles listados em `NUVEM.md`.

Um único worker é obrigatório nesta versão. Se ele cair após o SMTP aceitar a mensagem e antes de salvar o resultado, a tentativa seguinte pode duplicar o e-mail. As notificações no app são únicas por atividade. Escalar para vários workers exige fila/outbox com controle de concorrência; não basta iniciar outra cópia do comando. Edição/exclusão simultânea com envio já iniciado pode deixar um e-mail antigo em trânsito.

O código é gratuito para executar localmente. Hospedagem contínua e serviços de e-mail podem ter custos. Não há promessa de infraestrutura gratuita permanente ou de software sem erros.

## Validações realizadas

- 23 testes automatizados aprovados, também executados com pytest.
- Execução automática dos testes pelo GitHub Actions.
- Acesso manual validado no computador e no telefone pela mesma rede Wi-Fi.
- Recebimento real de lembrete por e-mail confirmado com Gmail.
- Inicialização dos lembretes em uma nova janela usando credencial protegida pelo Windows.

### Teste manual de envio de e-mail

Pré-condições: servidor e processo de lembretes ativos, Gmail configurado e conta cadastrada com endereço válido.

Passos:
1. Criar uma atividade para alguns minutos no futuro.
2. Marcar "Receber também por e-mail".
3. Salvar e manter a atividade como agendada.
4. Aguardar o horário e conferir o aplicativo e a caixa de entrada.

Resultado esperado: mensagem disponível na agenda e e-mail recebido.
Resultado obtido: recebimento do e-mail confirmado durante a validação manual.

### Investigação de falha

Durante a configuração, o envio falhou na autenticação SMTP.
Foram verificados os parâmetros carregados, o tamanho da senha de app e o endereço da conta remetente.
Após corrigir a entrada da credencial e o endereço de e-mail, a autenticação funcionou e o lembrete foi recebido.

## Estado atual e aprendizado

Projeto de estudo e portfólio de QA, executado localmente.
O computador precisa permanecer ligado com o servidor e o processo de lembretes ativos.
A hospedagem na nuvem está pendente.
As mensagens no aplicativo aparecem ao abrir ou atualizar a página; não há notificações push.

O projeto foi desenvolvido com apoio de IA, com execução dos testes e validações manuais pela pessoa responsável pelo portfólio.
Os testes fornecem evidências de funcionamento nos cenários avaliados e não garantem ausência de defeitos.
