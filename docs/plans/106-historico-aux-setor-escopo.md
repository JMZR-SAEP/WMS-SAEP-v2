# Plano — Histórico de requisições escopado para auxiliar de setor (#106)

## Escopo

`historico_requisicoes_visiveis_para` (`apps/requisicoes/selectors.py:266`) e
`requisicoes_visiveis_para` (`apps/requisicoes/selectors.py:87`) discordam sobre
o auxiliar de setor não-almoxarifado:

- o histórico concede a quem tem `papel.setores_em_escopo` — tupla que inclui os
  setores em que o ator é **auxiliar**, não só o que ele chefia;
- o detalhe concede visão de setor apenas a `papel.setor_chefiado_ativo_id`.

O auxiliar lista, portanto, requisições de terceiros do próprio setor e recebe
**404** ao clicar em "Ver" — tanto no card mobile quanto na linha da tabela
(`apps/requisicoes/templates/requisicoes/historico_requisicoes.html:83` e `:137`,
ambos para `requisicoes:detalhe`). A `docs/matriz-permissoes.md §4`, linha "Ver requisições
do setor", já diz **Não** para Aux. setor: o histórico é que está fora da matriz.

Decisão do grill registrada no issue: **negar** — alinhar o histórico à matriz,
não ampliar o detalhe.

**Muda:**

- `apps/requisicoes/selectors.py` — `historico_requisicoes_visiveis_para` troca
  `setores_em_escopo` por `setor_chefiado_ativo_id` e ganha a cláusula de
  criador, que preserva o critério de aceite 2.
- `apps/requisicoes/policies.py` — docstring de
  `pode_consultar_historico_requisicoes`: o acesso à página continua igual, mas
  a frase "espelha o universo" deixa de ser verdadeira para o auxiliar.
- `apps/requisicoes/tests/test_selectors.py` — casos de auxiliar de setor e o
  teste de coerência histórico ⊆ detalhe.
- `apps/requisicoes/tests/test_policies.py` — auxiliar de setor continua com
  acesso à página.
- `apps/requisicoes/tests/test_views.py` — auxiliar recebe 200 e nenhuma linha
  de terceiro.
- `docs/matriz-permissoes.md` — §5 passa a documentar a visibilidade do
  histórico de requisições, hoje ausente.

**Não muda:**

- `requisicoes_visiveis_para` — é o lado correto do desacordo; o detalhe fica
  intocado, e com ele o 404 para quem não pode abrir a requisição.
- `pode_consultar_historico_requisicoes` (comportamento) — o auxiliar continua
  entrando na página. Negar o acesso resolveria o 404 também, mas contraria o
  critério de aceite 2 ("aux continua vendo, no histórico, as requisições que
  ele criou") e transformaria um bug de listagem num 403 novo.
- `pode_filtrar_historico_por_setor` / `setores_do_historico` — o filtro de
  setor já é exclusivo de almoxarifado e superusuário; nada a ajustar.
- `estoque/selectors.py::movimentacoes_visiveis_para` (US-17) — continua
  concedendo ao auxiliar as movimentações do setor. Assimetria conhecida e
  **aceita** pelo grill; ver Riscos.
- Models, constraints, migrations — nenhuma mudança de schema. `make setup`
  não é necessário.
- Templates — nenhuma alteração de UI; a linha some da tabela por queryset.

## Arquivos alterados

| Arquivo | Ação |
|---|---|
| `apps/requisicoes/selectors.py` | Corpo de `historico_requisicoes_visiveis_para` (filtro + docstring) |
| `apps/requisicoes/policies.py` | Docstring de `pode_consultar_historico_requisicoes` |
| `apps/requisicoes/tests/test_selectors.py` | 4 casos novos na seção de histórico |
| `apps/requisicoes/tests/test_policies.py` | 1 caso em `TestPodeConsultarHistoricoRequisicoes` |
| `apps/requisicoes/tests/test_views.py` | 1 caso em `TestHistoricoRequisicoesView` |
| `docs/matriz-permissoes.md` | §5 — bullet de visibilidade do histórico de requisições |

## Implementação

Trecho final de `historico_requisicoes_visiveis_para`, do `papel_efetivo` em
diante:

```python
    papel = papel_efetivo(ator)
    if papel.eh_almoxarifado:
        return base_qs.filter(nao_rascunho)

    if not papel.setores_em_escopo:
        return base_qs.none()

    filtro = Q(criador_id=ator.pk)
    if papel.setor_chefiado_ativo_id is not None:
        filtro |= Q(setor_beneficiario_id=papel.setor_chefiado_ativo_id)

    return base_qs.filter(filtro & nao_rascunho)
```

Quatro decisões que o código embute:

1. **`setor_chefiado_ativo_id`, não `setores_em_escopo`.** É a correção do
   issue e o que alinha o histórico à matriz §4. `setores_em_escopo` mistura
   chefia e vínculo auxiliar (`apps/accounts/papeis.py:65-71`); só a chefia
   concede visão de terceiros. Chefe de almoxarifado não chega aqui — sai antes
   por `eh_almoxarifado` —, então o `and not papel.eh_chefe_de_almoxarifado`
   que `requisicoes_visiveis_para` precisa carregar não tem análogo neste ramo.
2. **Cláusula de criador, para atender o critério 2.** Sem ela o auxiliar
   passaria a ver histórico vazio, e a página deixaria de fazer sentido para
   ele. Com ela, o auxiliar vê exatamente o que criou — que é o que o detalhe
   já lhe concede como criador.
3. **A cláusula de criador vale para todo papel de setor, não só para o
   auxiliar.** Para o chefe ela é quase sempre redundante: a policy de criação
   (`resolver_escopo_criacao_requisicao`) limita o beneficiário a
   `setores_em_escopo`, e a requisição herda o setor do beneficiário, então o
   caso normal já cai na cláusula de setor. Ela só soma linhas para quem chefia
   um setor **e** cria fora dele — chefe que também é auxiliar em outro setor,
   ou chefe cujo próprio `setor` de lotação não é o que ele chefia. Nos dois
   casos o detalhe concede a mesma requisição, como criador. Um ramo
   `if papel.setor_chefiado_ativo_id is None` separado só para o auxiliar
   produziria o mesmo resultado com duas regras em vez de uma.
4. **Guarda `setores_em_escopo` vazio antes do filtro.** Solicitante puro
   continua com queryset vazio — sem essa linha, a cláusula de criador lhe
   daria as próprias requisições no histórico, ampliando o universo de um papel
   que a policy nem deixa entrar na página, e quebrando
   `test_historico_solicitante_puro_vazio`. A condição é a mesma de
   `pode_consultar_historico_requisicoes`, e é o que mantém policy e selector
   concordando sobre *quem* vê algo (o *quanto* cada um vê é que passa a
   divergir — daí o ajuste de docstring).

Sem `.distinct()`: o filtro toca apenas colunas da própria `requisicao`
(`criador_id`, `setor_beneficiario_id`, `estado`), sem join multivalorado, então
o `OR` não duplica linhas. `requisicoes_visiveis_para` carrega `.distinct()` por
herança de um filtro mais largo; copiá-lo aqui só adicionaria um `SELECT
DISTINCT` inútil antes do `annotate(Count('itens'))` que a view aplica.

A docstring da função troca o bullet

> chefe/aux de setor não-almox → requisições com `setor_beneficiario` nos
> setores do ator

por um par de bullets que separa chefe (setor chefiado) de auxiliar (só o que
criou), e passa a nomear a razão: o histórico não pode listar o que o detalhe
devolve 404.

## Estratégia de testes

Camada de selector, `apps/requisicoes/tests/test_selectors.py`, seção
`historico_requisicoes_visiveis_para`:

| # | Caso | Esperado |
|---|---|---|
| 1 | `aux_obras` + `req_historico_obras` (criada por `solicitante`, setor Obras) | **não** aparece — critério de aceite 1 e 3 |
| 2 | `aux_obras` + requisição não-rascunho criada pelo próprio `aux_obras` | aparece — critério de aceite 2 |
| 3 | `aux_obras` + rascunho próprio | **não** aparece — histórico não é "minhas requisições", mesma regra já testada para chefe e almoxarifado |
| 4 | `aux_obras`: histórico ⊆ `requisicoes_visiveis_para` | conjunto vazio na diferença — regressão direta do 404 |

O caso 4 é o teste do bug, não do sintoma: ele falha para qualquer regra futura
que volte a listar no histórico algo que o detalhe recusa, inclusive por um
caminho diferente do `setores_em_escopo`.

`test_historico_chefe_setor_ve_so_proprio_setor` já cobre a segunda metade do
critério 3 (chefe do setor vê a requisição de terceiro) e continua verde sem
alteração — `req_historico_obras` tem `setor_beneficiario` = setor chefiado.

Camada de policy, `apps/requisicoes/tests/test_policies.py`,
`TestPodeConsultarHistoricoRequisicoes`:

| # | Caso | Esperado |
|---|---|---|
| 5 | `AUX_OBRAS` (persona já existente, `setor_chefiado_ativo_id=None`) | `True` — a página continua acessível ao auxiliar |

Camada de view, `apps/requisicoes/tests/test_views.py`,
`TestHistoricoRequisicoesView`:

| # | Caso | Esperado |
|---|---|---|
| 6 | `aux_obras` faz GET no histórico com `req_historico_obras` no banco | 200 (não 403) e `req_historico_obras` fora do `page_obj` |

O caso 6 amarra policy e selector: sozinhos, o 5 e o 1 permitiriam uma
regressão em que o auxiliar recebe 403 (policy endurecida) ou volta a ver a
linha (selector afrouxado) sem que nenhum dos dois quebre.

Não coberto, e por quê: paginação/filtros do histórico para auxiliar
(`filtrar_historico_requisicoes` opera sobre o queryset já escopado — o recorte
não é o que mudou); auxiliar de setor com vínculo em mais de um setor (a regra
nova não olha mais para a lista de setores do auxiliar, então um segundo
vínculo não muda nada); auxiliar como beneficiário de requisição criada por
terceiro (fica fora do histórico e dentro do detalhe — direção segura, ver
Invariantes).

## Invariantes

`docs/matriz-invariantes.md` não tem linha própria para visibilidade de
requisição; a fonte é `docs/matriz-permissoes.md` §4/§5.

| Regra | Relação com esta mudança |
|---|---|
| Matriz §4, "Ver requisições do setor" = Não para Aux. setor | Passa a valer também no histórico. É o objetivo do issue. |
| Matriz §4, "Ver próprias requisições como criador" = Sim para todos | Preservado pela cláusula de criador (decisão 2). |
| Matriz §5, rascunho é creator-only | Preservado: `nao_rascunho` continua aplicado a todos os ramos não-superuser, inclusive ao rascunho do próprio ator. |
| Histórico ⊆ detalhe (invariante que o bug violava) | Passa a valer para todos os papéis: superuser (tudo/tudo), almoxarifado (`nao_rascunho` ⊆ `nao_rascunho ∪ criador`), chefe de setor (setor chefiado, mesma condição dos dois lados), auxiliar (criador ⊆ criador), solicitante (vazio). Testado no caso 4 para o auxiliar, que é o único papel onde a inclusão era falsa. |
| REQ-* (estado/transições) | Nenhuma transição, nenhuma escrita. Mudança é de leitura. |
| EST-* | Nenhum saldo tocado. |

## Riscos

| Risco | Avaliação |
|---|---|
| Assimetria com `movimentacoes_visiveis_para` (US-17) | Conhecida e aceita pelo grill, registrada no issue: o auxiliar continua vendo as **movimentações** do setor enquanto deixa de ver as **requisições** de terceiros do setor. Ampliar "aux supervisiona o setor" é decisão explícita pós-piloto, não escopo deste issue. Não há caminho novo para o 404 por aí: `historico_movimentacoes.html` exibe o `numero_publico` da requisição como texto, sem link para `requisicoes:detalhe`. |
| Auxiliar perde acesso que hoje usa | É a decisão do issue, e o acesso atual é parcialmente falso — metade das linhas devolve 404. O que ele mantém (as próprias requisições) é o que ele consegue abrir. |
| Histórico do auxiliar fica quase igual a "minhas requisições" | Real. A diferença é o rascunho, que aparece em "minhas" e não no histórico. Manter a entrada na navegação é escolha do critério 2; se o piloto mostrar que a página não paga o próprio custo para esse papel, a resposta é esconder a entrada, não voltar a listar o que dá 404. |
| Policy e selector deixam de "espelhar" | O acesso à página e o universo de linhas passam a ser regras distintas para o auxiliar. Endereçado pelo ajuste de docstring em `pode_consultar_historico_requisicoes` e pelo caso de teste 6, que trava a combinação das duas. |
| Migrations / schema | Nenhuma mudança de model. |
| Contrato OpenAPI | Projeto é server-rendered sem camada REST (AGENTS.md). Não se aplica. |
