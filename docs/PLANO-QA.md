# Plano de QA — primeira versão

Objetivo: verificar autenticação, isolamento, agenda e entrega de lembretes antes do uso. Testes automatizados usam banco temporário e e-mail em memória. SMTP real, responsividade em aparelhos e implantação precisam de validação manual posterior.

| ID | Critério de aceitação | Evidência automatizada |
|---|---|---|
| R01 | Cadastro grava senha com hash e e-mail normalizado | test_signup_hashed_normalized |
| R02 | E-mail duplicado e senha fraca são rejeitados | test_duplicate_email, test_weak_password |
| R03 | Login correto funciona; incorreto é rejeitado; logout encerra acesso | test_login_logout |
| R04 | Visitante precisa entrar | test_anonymous_blocked |
| R05 | Só é possível criar data futura no fuso de São Paulo | test_past_invalid, test_create_timezone |
| R06 | Um usuário não vê ou altera atividades de outro | test_isolation, test_read_isolation |
| R07 | Alteração exige POST e proteção CSRF | test_get_cannot_delete, test_csrf |
| R08 | Vencimento gera mensagem e e-mail, sem repetição normal | test_due_no_repeat |
| R09 | Futuras/concluídas não notificam; opção desativada não envia e-mail | test_future, test_completed, test_disabled_email |
| R10 | Falha SMTP preserva mensagem e tenta novamente | test_failure_retry, test_zero_send |
| R11 | Editar reagenda; excluir remove notificação | test_edit_resets, test_delete_cascade |
| R12 | Conteúdo inserido é escapado na tela | test_html_escape |

## Cenários manuais — pendentes

1. Chrome no Windows e navegador real no telefone: cadastrar conta, criar atividade, editar, concluir, excluir, sair e entrar; verificar layout a 360 px e navegação por teclado.
2. Criar lembrete para dois minutos depois, manter worker ativo, fechar navegador e abrir depois. Mensagem deve estar na caixa. Testar também opção sem e-mail.
3. Configurar SMTP de teste e confirmar recebimento real, remetente, horário e conteúdo. Conferir pasta de spam. Não usar dados pessoais de terceiros.
4. Na nuvem, desligar o computador e confirmar e-mail e mensagem. Reiniciar servidor e verificar persistência. Fazer backup e testar restauração em ambiente separado.
5. Interromper worker antes do vencimento, reiniciar depois: atividade vencida deve ser processada. Não testar a interrupção durante o envio como garantia de não duplicidade.
6. Simular falha SMTP e acompanhar retomada. Verificar que logs não revelam credenciais.

## Modelo de relato de bug

Título: mensagem não aparece após vencimento.
Ambiente: versão/commit, navegador, SO e fuso.
Pré-condições: conta conectada, worker ativo, atividade para 15h.
Passos: cadastrar; aguardar até 15h01; atualizar a agenda.
Esperado: mensagem com título e data.
Obtido: registrar o comportamento observado, sem inventar falha.
Evidências: horário, captura sem dados pessoais e logs sem segredos.
Severidade: justificar pelo impacto. Registrar reteste após correção.

## Critério para liberar uso

Suíte aprovada, cenários manuais essenciais aprovados, SMTP real testado, persistência e recuperação verificadas e controles de publicação implementados. Nunca declarar “zero bugs”. Registre limitações conhecidas, data, versão e resultado real.

## Apresentar no portfólio

Publique código, README, matriz requisito/teste, resultados de CI e relatos reais de defeitos corrigidos. Explique mocks, testes negativos, isolamento de dados, CSRF e testes de regressão. Declare assistência de IA na implementação e mostre sua capacidade de explicar, executar, alterar e depurar o projeto.
