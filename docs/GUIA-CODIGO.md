# Guia didático dos blocos

## 1. Caminho de uma ação

Quando você salva uma atividade, o navegador envia um POST. `urls.py` escolhe a view. A view verifica o login e passa os dados ao formulário. O formulário valida. O modelo grava no SQLite. A view redireciona à agenda e o template monta a página. Separar essas responsabilidades torna o código mais fácil de testar.

## 2. `manage.py`

O primeiro bloco escolhe `config.settings` como configuração. O segundo chama `execute_from_command_line`: é ele que permite usar os comandos `migrate`, `runserver`, `test` e nosso `process_reminders`.

## 3. `config/settings.py`

- Imports e `BASE_DIR`: localizam arquivos a partir da pasta do projeto.
- `DEBUG`, `SECRET_KEY`, hosts e origens: definem ambiente e segurança. Em produção uma chave própria é obrigatória. Não guarde credenciais no Git.
- `INSTALLED_APPS`: ativa autenticação, sessões, mensagens, arquivos estáticos e nosso módulo.
- `MIDDLEWARE`: aplica segurança, sessão, proteção contra CSRF e reconhecimento do usuário a cada requisição.
- `TEMPLATES`: indica onde ficam as telas e quais dados comuns elas recebem.
- `DATABASES`: configura SQLite; `DB_PATH` permite colocar o arquivo em armazenamento persistente.
- Validadores de senha: rejeitam senhas simples, numéricas ou semelhantes ao usuário.
- Idioma e fuso: apresentam português e São Paulo. `USE_TZ` permite gravar instantes de maneira consistente e converter na apresentação.
- E-mail: por padrão escreve no console. Variáveis de ambiente permitem ativar SMTP sem modificar a lógica de lembretes.
- Cookies, HTTPS e HSTS: proteções ativadas quando `DEBUG=0`; exigem implantação HTTPS correta.

## 4. `models.py` e migrações

`Task` representa uma atividade. `user` liga a atividade ao dono. Título, descrição e data são seu conteúdo. `completed` evita alertas de atividades concluídas. Os campos de e-mail guardam opção, tentativas, próximo horário de tentativa e envio confirmado pelo backend.

`Notification` representa a mensagem dentro do app. `OneToOneField` permite somente uma por atividade; `read` indica se foi lida. Excluir uma atividade remove sua mensagem por `CASCADE`.

`Meta` ordena atividades por horário e cria um índice para as consultas de vencimento. A migração `0001_initial.py` descreve a criação das tabelas. `migrate` aplica essa descrição ao banco; não edite o banco manualmente.

## 5. `forms.py`

`SignupForm` reutiliza a criação segura de usuários do Django. Usa o e-mail como nome de login. `clean_username` normaliza letras minúsculas e verifica duplicidade. `save` copia esse endereço para o campo de e-mail antes de salvar. O Django transforma a senha em hash.

`TaskForm.Meta` escolhe os campos que o usuário pode alterar: ele não pode enviar um campo `user` para trocar o dono. `due_at` usa um controle de data/hora do navegador. `clean_due_at` rejeita passado. Dados inválidos voltam à tela com mensagens.

## 6. `views.py`

- `signup`: exibe formulário no GET; cria e autentica no POST válido.
- `dashboard`: consulta somente atividades e mensagens do usuário conectado.
- `create`: atribui o dono a partir da sessão, nunca do navegador.
- `edit`: procura a atividade por identificador E dono; salva nova data e zera entrega anterior para reagendar.
- `delete`, `complete`, `read`: exigem POST. Cada uma busca o objeto com filtro de dono e altera somente o que a ação requer.

`login_required` redireciona visitantes ao login. `get_object_or_404` responde 404 se o objeto não pertence à pessoa. `require_POST` impede alterações por links GET. `{% csrf_token %}` nos formulários protege contra requisições forjadas.

## 7. `services.py`

`process_due(now=None)` recebe um horário opcional. Nos testes podemos passar um horário fixo sem esperar minutos de verdade.

Primeiro busca atividades vencidas e não concluídas. `get_or_create` cria a mensagem só se ela ainda não existir. Depois busca e-mails pendentes cuja próxima tentativa já pode acontecer.

Para cada envio monta assunto, corpo e destinatário; `send_mail` usa o backend configurado. Se falhar ou retornar zero, mantém pendência e agenda nova tentativa com espera crescente até 60 minutos. Se aceitar, salva `email_sent_at`. O retorno contém contagens de mensagens novas, e-mails aceitos e falhas. Os logs evitam expor dados pessoais.

Este serviço não depende da página aberta. Ele depende de um processo vivo e de banco disponível. A prevenção de duplicidade tem os limites documentados no README.

## 8. Comando `process_reminders`

`add_arguments` registra a opção `--loop`. `handle` chama o serviço e imprime os resultados. Sem `--loop`, executa uma vez: útil para testes ou um agendador externo. Com `--loop`, repete a cada 30 segundos. Execute apenas uma instância.

## 9. Templates e URLs

`base.html` define estrutura, estilo responsivo e botão de saída. Os outros templates herdam essa estrutura. `dashboard.html` percorre atividades e mensagens; `form.html` exibe formulários com erros; `registration/login.html` exibe entrada.

`{{ valor }}` escapa HTML automaticamente, reduzindo risco de scripts inseridos no título. CSS adapta espaçamento em telas pequenas. `config/urls.py` associa cada endereço a uma função ou à autenticação pronta do Django. `wsgi.py` permite que um servidor de produção execute a aplicação.

## 10. `tests.py` e CI

`setUp` cria usuários e uma atividade no banco isolado. Cada teste prepara uma condição, executa uma ação e verifica resultados com `assert...`. O backend `locmem` guarda e-mails em memória: nenhum e-mail real sai dos testes. `patch` simula SMTP indisponível. `Client(enforce_csrf_checks=True)` verifica rejeição de POST sem token.

A cobertura mostra linhas executadas, não comprova ausência de bugs. O workflow GitHub instala dependências, verifica migrações e executa a suíte automaticamente. Uma falha impede que o job apareça como aprovado.

## Exercício para seu portfólio

Escolha um teste, descreva o requisito que ele protege e remova temporariamente o filtro `user=request.user` de uma view. Execute a suíte, observe a falha de isolamento e restaure o filtro. Faça isso apenas em uma cópia local. Registre o resultado como evidência de que o teste detecta uma regressão real.
