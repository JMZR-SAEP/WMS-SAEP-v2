# Plano — #27 SCPI: consultar histórico de importações

## Scope

**O que muda:**
- `apps/estoque/policies.py` — novas funções `pode_consultar_historico_scpi` / `exigir_pode_consultar_historico_scpi`
- `apps/estoque/selectors.py` — nova função `listar_historico_importacoes_scpi`
- `apps/estoque/views.py` — nova view `historico_importacoes_scpi_view`
- `apps/estoque/urls.py` — nova rota `importacao-scpi/historico/`
- `apps/estoque/templates/estoque/historico_importacoes_scpi.html` — template de listagem
- `apps/estoque/tests/test_policies.py` — testes de policy
- `apps/estoque/tests/test_selectors.py` — testes de selector
- `apps/estoque/tests/test_views.py` — testes de view

**O que NÃO muda:**
- Model `ImportacaoSCPI` — sem alteração de schema
- Fluxo de preview e confirmação — sem alteração
- Nenhuma movimentação de saldo gerada

## Files touched

| Arquivo | Ação |
|---------|------|
| `apps/estoque/policies.py` | Inserir duas funções após `exigir_pode_confirmar_importacao_scpi` |
| `apps/estoque/selectors.py` | Inserir `listar_historico_importacoes_scpi` após `gerar_preview_importacao_scpi` |
| `apps/estoque/views.py` | Inserir `historico_importacoes_scpi_view` após `sucesso_importacao_scpi_view` |
| `apps/estoque/urls.py` | Adicionar path `importacao-scpi/historico/` |
| `apps/estoque/templates/estoque/historico_importacoes_scpi.html` | Criar template |
| `apps/estoque/tests/test_policies.py` | Adicionar `TestPodeConsultarHistoricoScpi` |
| `apps/estoque/tests/test_selectors.py` | Adicionar `TestListarHistoricoImportacoesScpi` |
| `apps/estoque/tests/test_views.py` | Adicionar `TestHistoricoImportacoesScpiView` |

## Test strategy

| Caso | Camada |
|------|--------|
| `superuser` pode, `chefe_almoxarifado` pode | policy unit |
| `usuario_inativo` não pode, `solicitante` não pode | policy unit |
| `exigir_*` levanta `PermissaoNegada` quando negada | policy unit |
| Retorna queryset vazio quando sem registros | selector |
| Retorna importações existentes ordenadas por `-importado_em` | selector |
| Não autenticado → 302 /login/ | view HTTP |
| Sem permissão (solicitante) → 403 | view HTTP |
| Superuser GET → 200 | view HTTP |
| Chefe almoxarifado GET → 200 | view HTTP |
| POST → 405 | view HTTP |
| Exibe metadados: arquivo_nome, arquivo_hash, importado_por, importado_em, status, totais | view HTTP |
| Sem importações → 200 com lista vazia (sem erro) | view HTTP |

## Invariants

- Histórico é read-only: nenhuma view altera saldo ou metadados
- Não expõe CSV bruto nem snapshot de preview
- Permissão: superuser + chefe de almoxarifado (conforme PRD #28)

## Risks

- Nenhum risco de concurrency (apenas leitura)
- Sem mudança de schema → sem migration necessária
