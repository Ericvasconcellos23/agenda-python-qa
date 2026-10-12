# Estratégia de Testes de API e Integração — Backend Agenda

Este documento formaliza a estratégia de testes automatizados do backend do **Minha Agenda**, implementada com **pytest**, **pytest-django** e **coverage**.

---

## 1. Objetivos da Estratégia

1. **Garantia de Isolamento Multi-tenant (BOLA / IDOR):** Provar que nenhum usuário consegue ler, editar, concluir ou excluir recursos pertencentes a outro usuário.
2. **Confiabilidade de Contratos HTTP:** Validar que todos os endpoints retornam os códigos de status HTTP corretos (200, 302, 403, 404, 405) e respeitam os métodos permitidos.
3. **Resiliência do Serviço Assíncrono:** Garantir idempotência na geração de alertas e comprovar o funcionamento do backoff exponencial em caso de falhas transitórias de rede/SMTP.
4. **Segurança de Entrada e Aplicação:** Blindar o backend contra XSS, ataques de força bruta/injeção e garantir proteções CSRF e hashing de senhas.
5. **100% de Cobertura de Código e Ramificações (Branch Coverage):** Auditar todas as instruções e caminhos condicionais (`if/else`) com o `coverage`.

---

## 2. Níveis e Dimensões de Teste

```
                 / \
                /   \     Testes de Resiliência & Worker
               /  E2E\    (Backoff exponencial, falhas SMTP, idempotência)
              /-------\
             /  IDOR   \   Testes de Autorização & Segurança
            / Segurança \  (Multi-tenancy, CSRF, XSS, Hashing, 404/403)
           /-------------\
          /  Endpoints &  \ Testes Funcionais & Boundary
         /   Contratos     \ (CRUD, limites de caracteres, fuso SP, 405)
        /-------------------\
```

### 2.1 Autenticação e Gestão de Sessão (`tests/test_auth_api.py`)
* **GET `/cadastro/`:** Renderização correta do formulário para visitantes (Status 200).
* **POST `/cadastro/` (Sucesso):** Criação de usuário com senha em hash PBKDF2, normalização do e-mail em minúsculas, login automático e redirecionamento 302 para `/`.
* **POST `/cadastro/` (Validações):**
  * E-mails duplicados case-insensitive (`ANA@...` vs `ana@...`).
  * Senhas fracas (curtas, puramente numéricas, muito comuns) via `@pytest.mark.parametrize`.
  * Divergência entre confirmação de senha (`password1 != password2`).
* **POST `/accounts/login/`:** Autenticação correta vs rejeição com mensagens adequadas para credenciais inválidas.
* **POST `/accounts/logout/`:** Invalidação imediata de sessão.
* **Acesso Anônimo:** Garantia de que rotas protegidas redirecionam para o login com parâmetro `?next=`.

### 2.2 Endpoints de Atividades / Tasks (`tests/test_tasks_api.py`)
* **GET `/` (Dashboard):** Consulta filtrada no banco exclusivamente para o usuário autenticado.
* **POST `/atividade/nova/`:**
  * Associação automática do usuário da sessão (`task.user = request.user`), impossibilitando envio forjado de proprietário.
  * Rejeição de agendamentos no passado (`clean_due_at`).
  * Fuso horário de São Paulo gravado e recuperado com precisão.
  * **Boundary Testing:** Título no limite máximo (150 caracteres) aceito vs acima do limite (151 caracteres) rejeitado.
* **GET/POST `/atividade/<pk>/editar/`:**
  * Reagendamento seguro: ao alterar data, zera contadores de tentativas de e-mail e deleta notificação in-app antiga.
  * Tentativa de editar tarefa já concluída retorna 404.
* **POST `/atividade/<pk>/concluir/`:** Transição de estado para `completed = True`.
* **POST `/atividade/<pk>/excluir/`:** Exclusão da tarefa e remoção em cascata (`CASCADE`) da notificação associada.
* **Controle BOLA / IDOR:** Usuário B tentando editar, concluir ou excluir tarefa do Usuário A recebe 404 Not Found.
* **Verbos HTTP Permitidos:** Ações mutativas (`excluir/`, `concluir/`) rejeitam GET com 405 Method Not Allowed.
* **CSRF Enforcement:** Requisições POST sem token CSRF recebem 403 Forbidden.

### 2.3 Notificações In-App (`tests/test_notifications_api.py`)
* **POST `/notificacao/<pk>/ler/`:** Atualização do status `read = True`.
* **Isolamento:** Usuário B tentando ler notificação do Usuário A recebe 404 Not Found.
* **Método HTTP:** Bloqueio de GET com 405 Method Not Allowed.

### 2.4 Worker Assíncrono e Resiliência (`tests/test_worker_service.py`)
* **Idempotência:** Múltiplas execuções do worker para um mesmo instante processam lembretes exatamente uma vez.
* **Tarefas Futuras e Concluídas:** Desconsideradas pela query otimizada com índices compostos.
* **Envio Opcional:** Tarefas com `email_enabled = False` geram notificação in-app e zero e-mails.
* **Simulação de Falhas SMTP (Mocking):**
  * Uso de `unittest.mock.patch` para simular queda de servidor de correio (`OSError`).
  * Verificação do cálculo de retentativa com backoff exponencial: `min(60, 2 ** min(attempts, 6))`.
  * Bloqueio de retentativa precoce e liberação na janela correta.
* **Comando CLI `process_reminders`:** Validação da execução única e com flag `--loop`.

### 2.5 Segurança de Aplicação (`tests/test_security_api.py`)
* **Prevenção de XSS:** Payloads com `<script>`, `<img>` e `<svg>` são devidamente sanitizados na renderização de títulos e descrições.
* **Resiliência a SQL Injection:** Strings maliciosas tratadas como literais via consultas parametrizadas do Django ORM.
* **Checagem de Ambiente de Produção:** Validação de que chave default com `DEBUG=0` dispara `ImproperlyConfigured`.

---

## 3. Padrão Arquitetural de Testes com Pytest

A suíte adota fixtures modulares em [`tests/conftest.py`](file:///home/esquilage/agenda-python-qa/tests/conftest.py):

| Fixture | Escopo / Papel |
|---|---|
| `configure_test_email` | Autouse: força `locmem.EmailBackend` para isolar rede. |
| `anon_client` | Cliente HTTP sem sessão para testar bloqueios e cadastro. |
| `user` / `other_user` | Modelos de usuários distintos para testes multi-tenant. |
| `auth_client` / `other_client` | Clientes autenticados com as respectivas contas. |
| `csrf_client` | Cliente com checagem rígida de token CSRF (`enforce_csrf_checks=True`). |
| `task_factory` | Fábrica parametrizável de atividades (`Task`). |
| `overdue_task` / `future_task` | Instâncias prontas para testes temporais e do worker. |

---

## 4. Métricas e Resultados de Cobertura

Configuração do [`.coveragerc`](file:///home/esquilage/agenda-python-qa/.coveragerc):
* `branch = True`: avalia todas as decisões lógicas (`if/else`).
* `show_missing = True`: evidencia linhas e ramos descobertos.

### Resultado da Execução:

```
======================= 75 passed in 25.22s =======================

Name                                                 Stmts   Miss Branch BrPart    Cover   Missing
--------------------------------------------------------------------------------------------------
lembretes/__init__.py                                    0      0      0      0  100.00%
lembretes/forms.py                                      33      0      6      0  100.00%
lembretes/management/__init__.py                         0      0      0      0  100.00%
lembretes/management/commands/__init__.py                0      0      0      0  100.00%
lembretes/management/commands/process_reminders.py      14      0      2      0  100.00%
lembretes/models.py                                     19      0      0      0  100.00%
lembretes/services.py                                   31      0      6      0  100.00%
lembretes/views.py                                      56      0      6      0  100.00%
--------------------------------------------------------------------------------------------------
TOTAL                                                  153      0     20      0  100.00%
```

---

## 5. Como Executar os Testes

```bash
# Execução direta com pytest
DEBUG=1 ./.venv/bin/pytest

# Execução com medição de cobertura
DEBUG=1 ./.venv/bin/coverage run -m pytest
DEBUG=1 ./.venv/bin/coverage report -m

# Gerar relatório visual HTML
DEBUG=1 ./.venv/bin/coverage html
```

