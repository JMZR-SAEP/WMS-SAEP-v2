# Denominação SCPI em CAIXA ALTA — normalizar na escrita (#184, fatia (a) da #173)

**Decisão (PR #192):** a importação SCPI grava `Material.nome` já em sentence
case. Não normaliza na exibição.

- Helper: `apps/core/texto.capitalizar_frase(texto)` — apresentação pura, sem ADR.
  Baixa a string toda e sobe a 1ª letra alfabética. NÃO usa `str.title()`/`|title`
  (quebram `3/4"`, `280G`) nem `capfirst` sozinho (não baixa ALL-CAPS no meio).
  Trata vazio/None → `''`.
- Chamado em `apps/estoque/services.py` na criação do `Material` (confirmar_importacao_scpi).
- Razão: CSV do SCPI é registro de origem e segue fiel em `ImportacaoSCPI`/arquivo;
  normalizar na exibição exigiria filtro em ~13 telas e deixaria o dado sujo no
  banco (ordenação/busca/admin). Seed de dev já nasce sentence case.

**`Lower('nome')` no `Material.Meta.ordering`: NÃO.** Com normalização na escrita
todo nome nasce sentence case; `ordering=('nome',)` já é estável. `Lower` exigiria
índice funcional para não virar filesort e não agrega garantia. Sem mudança de
model → sem migration.

Testes: `apps/core/tests/test_texto.py`;
`TestConfirmarImportacaoScpi::test_denominacao_scpi_em_caixa_alta_e_normalizada_na_escrita`.
