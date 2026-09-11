# Coordenação do ataque às issues — backlog pós-Etapa 8

**Documento vivo.** Ponto de partida para quem entra no backlog e ferramenta de acompanhamento para quem já está nele. Visão macro: o detalhe técnico vive na issue, aqui vive a **ordem, a dependência e o estado**.

Última atualização: **2026-09-11, décima passada, #179 mergeada + review endereçado** (PR `#201` **mergeada e fechada** pelo usuário — squash `9c56ef3` → **#179 fechada, auto-close funcionou**. Antes do merge, review do CodeRabbit endereçado via `/address-review` (commit `6ecfd52`): 4 achados reais + 1 nitpick. Corrigidos e resolvidos: sinal da fórmula de entregue líquida em `estado-transicoes-requisicao.md` (estorno de devolução soma de volta, não subtrai — reverte devolução), nome do selector em LED-06 de `matriz-invariantes.md` (`entregue_liquida_por_item` → `entregue_liquida_por_material`, divergência pré-existente que a issue #179 não causou), contrato de ledger em `CONTEXT.md` (Entregue líquida + Tipo de movimentação ainda omitiam `estorno_devolucao`), teste duplicado removido de `test_services.py`. **Não aplicado, com justificativa na thread:** achado major/segurança em `apps/estoque/services.py:990` pedindo policy check dentro de `estornar_devolucao_estoque` — o mutator espelha o irmão pré-existente `registrar_devolucao_estoque` (mesmo arquivo, não tocado), que também não valida policy própria; por contrato de camadas a autorização é responsabilidade do service de domínio chamador (`atendimento.py`), que já roda `exigir_pode_estornar_devolucao` antes de invocar, e é o único chamador de produção. Fica em aberto pra decisão humana de defesa em profundidade (follow-up nas duas funções, não regressão desta PR). Branch remota e local `feat/179-estornar-devolucao` apagadas (remota já tinha sumido no merge; local exigiu `-D` por ser squash merge). `main` local sincronizado com `origin/main`.

**Próximo passo do coordenador:** #171 segue aguardando o usuário decidir se fecha a issue (medição pronta, ver passada anterior). Fila de agente de implementação vazia — nada mais liberado sem decisão humana no momento. A ressalva sobre defesa em profundidade em `estoque/services.py` pode virar issue própria se o usuário topar.)

Última atualização anterior: **2026-09-11, nona passada, #171 medida (read-only, sem código)** (arquivo real do SCPI anexado pelo usuário no comment da issue — `todos_itens_cadastrados_de_marco_ate_setembro.csv`, 628 registros reais. Medido direto contra `_normalizar_csv_scpi`/`_parse_linhas_csv_scpi`/`gerar_preview_importacao_scpi` (`apps/estoque/selectors.py`), sem precisar de agente de dev: **volume** 762 linhas cruas → 629 pós-normalização (133 continuações, ~21%); **encoding** UTF-8 com BOM, decodifica sem erro; **CADPRO** 100% conforme `000.000.000`, zero duplicado; **denominação** nunca vazia, maior com 234 chars, não é CAIXA ALTA uniforme (memória antiga estava errada nisso); **header real** tem 21 colunas, não `CADPRO;DENOMINACAO;QUAN3` — nome vem de `DISC1`, e o parser já tolera isso via `_COLUNAS_NOME`, então não quebrou; **performance** 628 registros processados em ~19ms local. **Nenhuma quebra de código encontrada** — não abriu issue nova de correção. **Não mensurável localmente:** proporção de divergência WMS×SCPI real, porque o banco dev só tem 3 materiais sintéticos (tudo cai em "novo"); precisa do banco de produção. `project_scpi_csv_format` atualizada com o formato real. Achado corrigido só em memória, não em código.

**Próximo passo do coordenador registrado nesta passada:** reportar achados no comment da issue #171 e perguntar ao usuário se fecha (medição feita, nada quebrou, divergência real fica sem resposta possível neste ambiente) — aguardando OK antes de postar/fechar (ação pública no GitHub).

Última atualização anterior: **2026-09-10, oitava passada, #179 implementada e em PR** (decisão A/B do usuário chegou: **opção A**, registrada como comentário na issue. Branch `feat/179-estornar-devolucao`, service novo `estornar_devolucao` (requisições) + `estornar_devolucao_estoque` (estoque) espelhando `registrar_devolucao`, sem model `Devolucao` novo. Policy `pode_estornar_devolucao` segue `pode_estornar_requisicao` (chefe/superuser, exclui auxiliar). Achado técnico do shape confirmado na implementação: `Operacao.ESTORNAR_DEVOLUCAO` entrou em `_POLICY_POR_OPERACAO` no mesmo commit que `TRANSICOES` — sem isso `acoes_disponiveis()` quebra com `KeyError` pra requisição `ATENDIDA`. Checagem dupla de saldo: quantidade não pode exceder devolvida líquida (`devolvida_liquida_por_material`, selector novo) nem saldo disponível (matriz L83). Ripple: novo `TipoMovimentacaoEstoque.ESTORNO_DEVOLUCAO` toca partição hardcoded do histórico de movimentações (template+badge+testes de contagem), corrigido no mesmo commit. Gates verdes: 2825 pytest, ruff/mypy. **Correção de topologia no caminho:** PR nasceu por engano no fork `upstream` (`joaozuneda6#77`, memory desatualizada) — fechada sem merge, reaberta no origin como `JMZR-SAEP#201`, `Closes #179`. `project_git_remotes_topology` já registrava a virada pro origin desde 08/09; o índice `MEMORY.md` e o "Como usar" deste doc estavam com resumo velho, corrigidos. **Próximo passo do coordenador registrado nesta passada:** aguardar review/CI de verdade da PR #201 (checar comentário do CodeRabbit, não só o check — ver `project_coderabbit_inactive_and_stacked_merge`). #171 (medir CSV real) segue livre pra rodar em paralelo, read-only, sem decisão pendente.)

Última atualização anterior: **2026-09-10, sétima passada, #180 implementada e fechada** (implementação disparada a partir do shape, branch `feat/180-inativar-reativar-material`. **PR `JMZR-SAEP#200` mergeada** (`3230f34`) → **#180 fechada, auto-close funcionou**. `pode_gerir_catalogo` aceita `eh_chefe_de_almoxarifado`; admin do Django fica deliberadamente desacoplado dessa policy e continua superusuário-only (superfície edita todos os campos do material, não só `ativo`). Service novo `reativar_material` (espelha `desativar_material`, idempotente, sem checagem de saldo). UI em `lista_materiais.html`: botão+modal por cartão.

**CodeRabbit revisou de verdade desta vez** (repo não estava mais em modo "skip review manual"). 2 achados reais, ambos corrigidos num segundo commit: (1) major — `save_model` deixava o material sem `SaldoEstoque` se não houvesse `Estoque` ativo, invisível em `listar_materiais_com_saldo`; corrigido validando *antes* de `super().save_model()`, recusa com `ConflitoDominio`. (2) minor — o harness compartilhado de contrato de modal (`CenarioModal`) nunca provava mutação real em cenário `muta=True`; o `reativar_material` foi o **primeiro cenário `muta=True` do repo inteiro** (todo cenário anterior era `muta=False`), e nenhuma view mutante jamais teve essa prova. Campo novo `estado_esperado` em `apps/core/tests/contrato_modal.py`, comparado após 204 — achado que vale para qualquer app que ganhe cenário mutante no futuro, não só estoque.

Gates: 2796 pytest, ruff/mypy verdes. Verificado ao vivo no navegador (login como chefe, inativar/reativar com saldo zerado, e o 422 do erro reabrindo o modal).

**Próximo passo do coordenador:** #179 segue escalada — decisão A/B (quantidade-contra-agregado vs model `Devolucao` próprio) pendente do usuário, shape completo aguardando resposta. #171 (medir CSV real) livre pra rodar em paralelo, read-only. Fila de agente de implementação vazia — nada mais liberado sem decisão humana no momento.)

Última atualização anterior: **2026-09-10, sexta passada, PR #199 em review + shapes #179/#180** (PR `#199` (#170) com CI 100% verde — ruff format, ruff check, mypy, css build, migrations, pytest, navegador. `CodeRabbit` ainda `PENDING`, sem veredito. Enquanto a review corre, 2 agentes `Plan` read-only em paralelo (sem banco, sem app):

**#180 — shape completo, liberada para implementação.** `desativar_material` (`apps/estoque/services.py:822-863`) é o molde exato pra `reativar_material` (idempotente, sem checagem de saldo — reativar não tem o mesmo risco que desativar). Policy `pode_gerir_catalogo` passa a aceitar `eh_chefe_de_almoxarifado` além de superusuário. UI entra em `lista_materiais.html`, botão+modal por card (padrão de `requisicoes/detalhe.html:229-234`, não tela de detalhe nova — ela não existe pra material). 3 decisões de detalhe **não-bloqueantes** com default proposto no shape (cor do botão via Regra da Reversão Não é Erro, texto do modal avisando saldo zerado, simetria do caminho reativar em `admin.py`). 12 passos, arquivos: `policies.py`, `services.py`, `views.py`, `presentation.py`, `lista_materiais.html`, `urls.py`, `admin.py` + testes.

**#179 — shape completo, mas com 1 decisão humana bloqueante.** Devolução hoje não tem model próprio — é timeline+ledger agregado (`entregue_liquida_por_material`, confirmado por `test_registrar_devolucao_double_count_respeita_liquida`). Decisão em aberto: **(A)** estornar por quantidade contra o agregado do ledger, sem model novo, mesmo padrão de `registrar_devolucao` — **recomendação do shape**, menor mudança — vs **(B)** model `Devolucao` com identidade/estado próprios (espelha `SaidaExcepcional`), schema maior, sem pedido explícito no corpo da issue. Achado técnico válido pras duas opções: `Operacao.ESTORNAR_DEVOLUCAO` **precisa** entrada em `_POLICY_POR_OPERACAO` (`apps/requisicoes/selectors.py:34`) assim que entrar em `TRANSICOES`, senão `acoes_disponiveis()` quebra com `KeyError` pra toda requisição `ATENDIDA`. Policy segue o padrão de `pode_estornar_requisicao` (chefe apenas, exclui auxiliar de almoxarifado), não o de `pode_registrar_devolucao` (que aceita auxiliar). 13 passos, arquivos: `requisicoes/services/atendimento.py`, `estoque/services.py`, `requisicoes/policies.py`, `requisicoes/transitions.py`, `estoque/selectors.py`, `requisicoes/selectors.py`, `requisicoes/models.py`, `estoque/models.py` + testes.

**Próximo passo do coordenador:** aguardar review/CI de verdade da #199 (checar comentário do CodeRabbit, não só o check — ver `project_coderabbit_inactive_and_stacked_merge`). Escalar decisão A/B da #179 ao usuário. #180 pronta pra virar ticket de implementação assim que a fila de banco único liberar (depois de #170 mergear — implementação é sempre sequencial, Postgres único).)

Última atualização anterior: **2026-09-10, quinta passada** (as 4 decisões humanas da "Disparar cedo" **chegaram** nos comentários das issues, respondidas por `joaorighetto` 2026-09-10. Todas destravadas, saem de `needs-info`:
- **#170** — "Recusar" ≠ "Cancelar". "Recusar" **mescla com *retornar para rascunho*** (chefe devolve requisição sem sentido p/ ajuste; transição de estado p/ rascunho, **não** encerra). "Cancelar requisição" = anular/deletar; dono = criador (desistência) **ou** chefe de almoxarifado (restrição que impede completar); **proibido depois da entrega**. Não é `layout` nem `clarify` puro — muda a máquina de estados. Precisa de **shape**.
- **#171** — export real anexado: `todos_itens_cadastrados_de_marco_ate_setembro.csv` (catálogo mar–set). Próximo: medir o arquivo real (linhas, encoding, denominação mais longa, continuação, % divergência); cada quebra vira issue própria.
- **#179** — **"Entra"** no MVP. Vira issue de implementação: op de domínio `estornar_devolucao` com checagem de saldo disponível (L83), par de policy (`pode_`/`exigir_pode_`), service com `ator_id` + transição + exceção de domínio, testes de policy e de service.
- **#180** — **"UI de produto"**. Server-rendered seguindo o design system, consome `desativar_material` + `reativar_material` (a criar); `pode_gerir_catalogo` passa a aceitar `eh_chefe_de_almoxarifado`, testes acompanham. A matriz L74/§3 **não** recua.

Fila de agente ainda **vazia** (nenhum agente disparado nesta passada). Onda 7 (#194–#198) + estes 4 aguardam disparo. Ordem sugerida da onda de análise read-only paralela: `Plan` #194, `impeccable shape`/`Plan` #170, `Plan` #179, `Plan` #180, `Explore` #171 (sem subir app — banco sujo). Implementação sempre sequencial (banco PostgreSQL único).)

Última atualização: **2026-09-10, quinta passada, shape #194 + #170** (2 agentes `Plan` read-only em paralelo, sem subir app, sem banco.

**#170 — shape completo, pronto pra implementação.** Achado: "cancelar" já é exatamente o que a decisão humana pediu (`transitions.py:68-80`, guarda pós-entrega já existe, nada a mudar). Só "recusar" muda: deixa de ser transição-para-estado-terminal (`EstadoRequisicao.RECUSADA` é removido) e vira variante de `retornar_para_rascunho` (TR-006) — o service escolhe o evento de timeline (`RECUSA` vs `RETORNO_RASCUNHO`) pelo papel do ator (chefe decidindo por terceiro vs criador/beneficiário agindo por si), replicando o padrão que `REGISTRAR_ATENDIMENTO` já usa (uma operação, múltiplos eventos possíveis). Sem policy nova, sem service novo — funde `recusar_requisicao` em `retornar_para_rascunho`. 13 passos sequenciais com migração incluída (remove `RECUSADA` do enum), cascata em `copia.py` (`ESTADOS_COPIAVEIS` perde `RECUSADA`), `views.py` (chip "Exceções" do histórico), `presentation.py` (copy da notificação), `docs/estado-transicoes-requisicao.md` (TR-011 vira nota de variante de TR-006). Sem decisão humana pendente — **liberada para implementação**. Arquivos: `transitions.py`, `models.py`, `services/ciclo_vida.py`, `policies.py`, `views.py`, `detalhe.html`, `docs/estado-transicoes-requisicao.md`.

**#194 — shape completo, mas com 6 decisões humanas pendentes antes de codar.** 3 premissas do corpo da issue verificadas como erradas/parciais: (1) as filas **não têm** toggle de ordenação hoje (`ordenacao_data.html:71-83` documenta a decisão consciente de FIFO sem inversão — a issue descreve um estado que o código já não tem); (2) o placeholder truncado provavelmente **não** afeta o catálogo — `lista_materiais.html` usa string mais curta e diferente da das 3 filas/minhas-requisições; (3) "ordenar por setor" só faz sentido em `fila_atendimento` (multi-setor) — em `fila_autorizacao` (escopada a um setor só) é no-op.

Sub-itens do shape: sinal de idade no cartão (precisa limiar de negócio), sinal de saldo no cartão (precisa selector novo vetorizado, reusar `saldos_por_materiais`), quantidade no cartão (ambíguo: linhas de item já existe vs total de unidades não existe), ordenação por saldo/setor (precisa decisão de escopo + mecânica HTMX, filas nunca tiveram swap parcial), travessia por teclado j/k (precisa decisão de acessibilidade — WCAG 2.1.4 exige atalho de tecla única ser desligável/remapeável), placeholder truncado (trivial, mas confirmar escopo do catálogo por medição antes). Achado à parte: "multi-seleção/ação em lote" e "continuidade PRG" aparecem no "Problema" da issue mas **não** entram na seção "Escopo" nem em "Fora de escopo" — risco de ficar esquecido, precisa decisão explícita (virar spin-off nomeado ou descartar).

Ordem de ataque sugerida (depois das decisões): placeholder → selector de saldo vetorizado → sinal no cartão → ordenação → teclado (por último, depende do cartão final estar estável). Arquivos: `selectors.py`, `views.py`, `fila_autorizacao.html`, `fila_atendimento.html`, `ordenacao_data.html`, `cartao-alvo.js`, `DESIGN.md`.

**Próximo passo do coordenador:** disparar implementação de #170 (liberada). #194 aguarda respostas às 6 perguntas antes de virar ticket de implementação — escalado ao usuário.)

Última atualização: **2026-09-10, quinta passada, #170 implementada e em PR** (implementação disparada, gates locais verdes 2762 pytest + 79 navegador + ruff/mypy — achado no caminho: `test_navegador_modal_foco.py` sobrou da varredura do agente, ainda mirava `confirmar-recusar`/`modal-recusar-motivo` (id velho), corrigido para `confirmar-retornar`/`modal-retornar-observacao`. `docs/design-system.md` também tinha 7 referências desatualizadas (modal-id, `danger`→`warning`, linha própria de "recusar" na tabela de glifo, painel de decisão) — resolvidas num segundo commit docs-only, disparado como follow-up separado. **PR aberta:** `JMZR-SAEP#199`. Decisões #194 postadas como comentário na issue: https://github.com/JMZR-SAEP/WMS-SAEP-v2/issues/194#issuecomment-5620772786.

**Próximo passo do coordenador:** aguardar review/CI da PR #199 (CodeRabbit responde no origin, mas checar comentários de verdade, não só o check verde — ver `project_coderabbit_inactive_and_stacked_merge`). Depois do merge, #194 está desbloqueada para virar ticket de implementação (shape + decisões já registrados nesta memória e no comentário da issue) — única pendência é a sequência de banco único (#170 primeiro, já em voo).)

Última atualização anterior: **2026-09-10, quarta passada** (backlog commitado `52a1c2b`. **Critique `/impeccable` rodada 3 rodada** — dual-agent, slug `apps`, like-for-like. Nota: 21 → 27 → **32/40** ("Good"). P0: 1 → 2 → **0**. Detector determinístico limpo (0 findings). Snapshot `.impeccable/critique/2026-09-10T13-45-33Z__apps.md`. Achado central: o sistema visual está maduro, o débito agora é de **fluxo e cópia** — heurística 7 (flexibilidade, nota 2) é o teto, nenhuma onda tocou vazão de fila. **5 issues abertas (onda 7): #194–#198**, todas `ready-for-agent`. Ordem: **#194 → #195 → #196/#197/#198**. Ressalva: os 2 agentes da critique colidiram no browser/banco de dev — teste interativo de B não-confiável, banco sujo (sem `make setup`, decisão do usuário). Ainda pendente: os pedidos de decisão humana da "Disparar cedo" (#170, #171, #179, #180) **não** foram disparados nesta passada.)

Última atualização anterior: **2026-09-10, terceira passada** (a #190 — spin-off da #186 — **mergeou e fechou** via PR `JMZR-SAEP#193`, `50e1d36`, auto-close (5ª vez seguida no `origin`). Gates verdes: 2770 pytest, 79 navegador, ruff/mypy. **A fila de agente está vazia.** Onda 6 (#173) completa + spin-off #190 completo. Todo o aberto (7 issues) é humano-bloqueado: `ready-for-human` (#172, #174) ou `needs-info` (#169–#171, #179, #180). Próximo movimento do coordenador: (a) disparar os pedidos de decisão humana da seção "Disparar cedo" (#170, #171, #179, #180) e (b) a próxima rodada de critique está **liberada** — onda 6 fechada, a regra que a bloqueava não vale mais.)

Última atualização anterior: **2026-09-10, segunda passada** (a #184 — fatia (a) da #173 — **mergeou e fechou** via PR `JMZR-SAEP#192`, `08972ac`, auto-close (4ª vez seguida no `origin`). **Onda 6 completa**: #184/#185/#186/#187 fechadas, **#173 (guarda-chuva) fechada**. Único item acionável por agente restante: **#190** (spin-off da #186) — **análise disparada** nesta passada (1 `Explore` read-only). Todo o resto aberto é `ready-for-human` (#172, #174) ou `needs-info` (#169–#171, #179, #180).)

Última atualização anterior: **2026-09-10** (a #186 — fatia (c) da #173 — **mergeou e fechou** via PR `JMZR-SAEP#191`, `a47184a`, CI verde, auto-close (3ª vez seguida no `origin`). Restam da onda 6 só a fatia (a): **#184** — implementação **disparada** nesta passada (branch `feat/184-copy-vocabulario`, 1 agente, sequencial). Fechar a #184 fecha a #173. Independente: **#190** (spin-off da #186, `ready-for-agent`).)

Última atualização anterior: **2026-09-09, terceira passada** (#186 e #184 analisadas — 2 `Explore` read-only. #186: item "drawer corta Sair" rebaixado (clip já corrigido em `df20393f`), gêmeo do bug de ordem de foco virou **#190** (spin-off, footer de todo modal), 3 itens saem por serem produto. #184: 4 itens procedem; normalização da denominação SCPI decidida **na escrita** (helper `apps/core/texto.py::sentence_case` novo). Ordem de implementação: **#186 → #184**, sequencial. Ver "A #186 na prática" e "A #184 na prática".)

## Como usar

- Antes de pegar trabalho: leia o quadro de estado e a ordem de ataque; pegue o primeiro item desbloqueado.
- Ao fechar algo: mova a linha para "Concluído", atualize a onda e registre o que a conclusão desbloqueou.
- Não replique aqui o conteúdo da issue. Se você está copiando parágrafo de issue para cá, está no lugar errado.
- Issues e PRs vivem os dois no origin `JMZR-SAEP/WMS-SAEP-v2` (desde 08/09/2026; fork `upstream` saiu do fluxo — ver `project_git_remotes_topology`).

## Origem deste backlog

Tudo aqui nasceu da **Etapa 8** (auditoria de frontend do produto inteiro) e da sua remedição. Duas medições heurísticas, mesmo alvo, mesmo método dual-agent:

| Rodada | Data | Nota | P0 | P1 |
|---|---|---|---|---|
| Etapa 8, Fase 2 | 2026-09-01 | 21/40 | 1 | 3 |
| Remedição (#165) | 2026-09-03 | 27/40 | 2 | 2 |
| Rodada 3 (pós-onda 6) | 2026-09-10 | **32/40** | 0 | 2 |

Snapshots em `.impeccable/critique/` (diretório local, gitignored). O plano de origem é `docs/plans/audit-frontend-restante.md`, seção "Depois do plano".

**A tese central que a remedição revelou, e que organiza toda a ordem abaixo:** *as correções da Etapa 8 pararam no chamador, não desceram para o componente.* O `4,38:1` de contraste está diagnosticado por escrito no comentário do template que o corrigiu, e o componente que 7 telas incluem continua emitindo o par. Mesmo padrão no badge: 9 variantes migradas para token, 4 esquecidas na paleta crua. Por isso o eixo componente+guarda (#177 → `quantidade.html` → #166) tem prioridade alta apesar de nenhuma das suas peças ser P0.

## Quadro de estado

**Concluído**

| # | O quê | Como fechou |
|---|---|---|
| 165 | Remedir a baseline heurística | Segunda medição rodada em 2026-09-03: 21 → 27. Gerou #175, #176 e #177. |
| 175 | Notificação afirmava estado que nunca reconsultava (P0) | PR #61, merged 2026-09-04. Sino passou de 14 para 4 e passou a bater com a fila. Decisão de produto registrada: `/notificacoes/` é **diário**, não caixa de entrada — aviso vencido fica visível marcado "Resolvida" e sai só da contagem. |
| 176 | Laço `home()` → `/admin/` + dono da importação SCPI | PR #62 e PR #63, ambos merged. Issue fechada em 2026-09-04 com comentário linkando os PRs e os spinoffs. |
| 168 | `input.css` na árvore de estáticos, storage customizado | PR `joaozuneda6/WMS-SAEP-v2#65`, squash `c3f7fb1`, merged 2026-09-04. Issue fechada. |
| 177 | 4 variantes cruas de `badge.html` | PR `joaozuneda6/WMS-SAEP-v2#66`, squash `0ee1949`, merged 2026-09-04 (empilhada sobre a #65, retargetou pra `main` sozinha assim que a #65 mergeou). Issue fechada. Nomenclatura: `orange`→`cancel`, `indigo`→`consumption`, `violet`→`reversal`, `yellow`→reuso de `amber`. |
| — | `quantidade.html`: contraste da unidade + `tom` não propagava pra `referencia` | PR `joaozuneda6/WMS-SAEP-v2#68`, merge `421ce15`, merged 2026-09-04. Sem issue própria. |
| 166 | Varredura de contraste na lane Navegador (par pai/filho) | PR `joaozuneda6/WMS-SAEP-v2#69`, merge `95e8018`, merged 2026-09-04. Issue fechada. Emendou a ADR-0019: 4º critério de admissão ("cascade resolvida e pipeline de cor") e o gatilho de "~15 casos" deu lugar ao relógio. Deixa pendente uma extensão: `estoque:preview_importacao_scpi` ficou fora (upload multipart), então o guarda nasce cego para o `bg-primary-subtle` que originou o eixo. |

**Ondas 4 e 5 — mergeadas e fechadas em 2026-09-08**

| # | PR | Merge | O que entregou |
|---|---|---|---|
| 182 | `joaozuneda6#70` | `9e52881` | `listar_saidas_excepcionais` perdeu o `ator_id` morto. Levou nota normativa ao `CONVENTIONS.md`: `ator_id` em selector é reservado ao sufixo `_visiveis_para`. |
| 183 | `joaozuneda6#75` | `46ee10c` | Contagem do sino saiu do `except Exception` com fallback zero: tolera só `django.db.Error` e devolve `None`. **Issue fechada manualmente em 2026-09-08** — de novo o merge não a fechou, terceira vez que a mesma armadilha cobra. |
| 167 | `joaozuneda6#71` | `43b6dee` | Legenda do preview SCPI **removida**, não corrigida — ver decisão abaixo. |
| 178 | `joaozuneda6#72` | `f3dd967` | Marcador EST-07 restrito ao almoxarifado, com `pode_consultar_divergencias_criticas` nova e os operandos `Físico`/`Reservado` gated. Bullet de catálogo na matriz §5. |
| 181 | `joaozuneda6#73` | `4fdf1e0` | `marcar_lida_view` passou a consumir a policy; negativa vira `Http404`. Cláusula de atividade no selector, corrigindo o USR-01. Bullet de notificações na matriz §5. |

**Armadilha de processo, custou uma rodada inteira.** Os corpos das quatro PRs diziam "issue fechada manualmente após o merge, já que a issue vive no outro remote" — e ninguém fechou. O merge não fecha issue de outro remote, e `Closes #N` no corpo também não atravessa. **Fechar é passo manual explícito depois do merge**, não consequência dele. As quatro passaram quatro dias abertas dizendo que o trabalho estava por fazer.

**Onda 6 — fatias (d) e (b) fechadas em 2026-09-09**

| # | PR | Merge | O que entregou |
|---|---|---|---|
| 187 | `JMZR-SAEP#188` (6 commits) | `d2db3b3` | As seis peças da fatia (d). Suíte 2729 ✅, Navegador 71 ✅, ruff/mypy ✅. Ver "A #187 na prática" abaixo. **Auto-close funcionou** — o merge fechou a issue sozinho, sem passo manual, validando a topologia nova. |
| 185 | `JMZR-SAEP#189` (8 commits) | `11a6d65` | As 5 entregas da fatia (b). Revisado por `cavecrew-reviewer` (1 nit 🔵) + `revisor-camadas` + 2 achados 🟡 do `joaorighetto` + 2 achados 🟡 do CodeRabbit (disparo manual) — todos corrigidos, threads resolvidos (ver "Achados de review da #189" e "Achados do CodeRabbit na #189" abaixo). **Auto-close funcionou** (2ª vez seguida). Job `navegador` vermelho no merge por flake de infra (`apt` Hash Sum mismatch no repo do Chrome), não código — rerun disparado. Escopo travado — ver "A #185 na prática". |
| 186 | `JMZR-SAEP#191` | `a47184a` | Fatia (c): navegação, ordem de foco (`flex-col-reverse` em `detalhe.html`/`copiar_confirmacao.html`), `focus-visible` na nav e na marca, heading da região de resultados do preview SCPI. CI verde (ruff/mypy/css build/migrations ✅). **Auto-close funcionou** (3ª vez seguida). O ponto global (`_modal_body.html`) ficou de fora — é a **#190**. Ver "A #186 na prática". |

**Em andamento**

_(vazio — nenhum agente disparado ainda na onda 7)_

**Onda 7 — critique `/impeccable` rodada 3 (aberta 2026-09-10)**

Nota `apps` 21 → 27 → **32/40**. Todas `ready-for-agent`. Ordem: **#194 → #195 → #196/#197/#198** (as três últimas independentes entre si, sequenciais só pelo banco compartilhado).

| # | O quê | Sev | Nota |
|---|---|---|---|
| 194 | Filas de trabalho não são feitas para vazão — triagem, ordenação, teclado no cartão de fila | P1 | Prioridade 1 (decisão do usuário). Começa com `/impeccable shape` ou Plan — várias peças, "autorizar inline no cartão" é sub-item de UX própria. Inclui o placeholder de busca truncado a 375px. Trava a heurística 7 (nota 2). |
| 195 | Modal de autorizar não carrega o déficit de saldo ("autorizar-e-quicar") | P1 | Só UI/cópia + `acoes_disponiveis` considerar saldo (decisão do usuário: **sem** pergunta de autorização parcial). Inclui foco na rejeição (volta como flash, não pelo `error_summary`). |
| 196 | Detalhe: painel de ação destrutiva precede a ação primária | P2 | `layout` + `quieter`. Aplicar ao caso inline a ordem que o banner não-inline já usa. |
| 197 | Notificações: cópia no passado, sopa de 3 badges, "marcar como lida" com afordância fraca | P2 | `clarify` + `quieter`. |
| 198 | Fatia de cópia miúda — vocabulário do login, `descricao` duplicada no modal, "Remover" em linha única, caixa do `<title>` "Nova Requisição" | P3 | Estilo #184, agrupada num PR. |

Fora do slate (registro, sem issue): marcadores de timeline uniformes (`slate-300`, sem distinção entre criação/autorização/recusa/estorno) e trigger azul da saída excepcional. Candidatos a próxima rodada.

**Onda 6 — spin-off #190 fechado em 2026-09-10**

| # | PR | Merge | O que entregou |
|---|---|---|---|
| 190 | `JMZR-SAEP#193` | `50e1d36` | Footer global `_modal_body.html`: `flex-col-reverse`→`flex-col` sem mexer no DOM (ordem do DOM = leitura = foco), WCAG 2.4.3. Proibição de `flex-col-reverse`/`order-*` de eixo vertical abaixo de `sm` virou **absoluta** no `DESIGN.md` §Layout (nota de Fechamento 2026-09-10, #190) — a exceção temporária rastreada que a #186 deixou para o `<footer>` foi removida. Caso novo na lane navegador (`test_navegador_ordem_foco.py`: mede `top` dos botões do footer a 375px vs ordem de Tab) + guarda por string em `test_modal.py`. Gates: 2770 pytest ✅, 79 navegador ✅, ruff/mypy ✅. **Auto-close funcionou (5ª vez seguida).** |

**Onda 6 — fatia (a) fechada em 2026-09-10 → #173 fechada**

| # | PR | Merge | O que entregou |
|---|---|---|---|
| 184 | `JMZR-SAEP#192` | `08972ac` | Fatia (a) da #173. 4 itens: rótulo de rota × tela (regra #160, nav segue a página), grafia `WMS-SAEP` (`login.html` era o único outlier), denominação SCPI normalizada **na escrita** (helper novo `apps/core/texto.py::capitalizar_frase` chamado em `services.py`), asterisco de obrigatório suprimido no login (exceção registrada no DESIGN.md). Revisado: `revisor-camadas` (1 BAIXA — renomeou `sentence_case`→`capitalizar_frase`), `cavecrew-reviewer` (2 🟡 descartados), feedback P2. **Auto-close funcionou (4ª vez seguida)** — fechou #184 e, por tabela, a #173 (guarda-chuva). |

**A #186 na prática — implementada e fechada via PR `JMZR-SAEP#191` (`a47184a`, 2026-09-10). 1 item rebaixado, 1 gêmeo virou #190, 3 itens saem por serem produto (análise 2026-09-09).**

| Item da issue | Veredito da análise | Decisão |
|---|---|---|
| drawer corta "Sair" | **mal enquadrado.** O clip já foi corrigido em `df20393f` (2026-08-12, na `main`): `input.css:667` tem `max-height: calc(100dvh - …)` + `overflow-y:auto` + `overscroll-behavior:contain`. Não há `overflow:hidden` nem colapso de `flex-basis`. Sobra só falta de affordance de scroll (sem fade/sombra; o padrão existe em `input.css:802` mas só horizontal p/ tabelas). | Rebaixado a cosmético. Fade de scroll no `.app-bar__menu` ⇒ `input.css` ⇒ `make css-build`. Item menor da fatia. |
| ordem de foco `flex-col-reverse` | **procede — item mais sério.** `requisicoes/detalhe.html:270` (`flex-col-reverse` sem `sm:`), WCAG 2.4.3. Comentário `:263-268` documenta o anti-padrão como se fosse certo. A ≥640px (`sm:flex-row`) visual e foco coincidem. **Gêmeo não-citado:** `components/_modal_body.html:198` (footer de TODO modal) + `requisicoes/copiar_confirmacao.html:62`. | #186 corrige os 2 pontos locais (`detalhe.html`, `copiar_confirmacao.html`). O ponto global (`_modal_body.html`) virou **#190** — mexer nele arrasta as 11 telas da varredura #166. |
| focus-visible ausente na nav | **procede.** 11 links (`core/partials/_side_nav.html:16-25`, só `rounded-md hover:…`, zero `focus-visible:`) + a marca (`.app-bar__brand`, `input.css:454` sem `:focus-visible`). Viola `design-system.md:220-223` + `DESIGN.md:534/580`. Drawer mobile (`.app-bar__menu-item`) **tem** anel (`input.css:717`). As 4 classes canônicas já estão no `app.css` — links não precisam de `make css-build`; a marca precisa se feita via `input.css`. | Adicionar o anel canônico aos links e à marca. Cosmético/consistência (issue mesma diz "não é falha WCAG"). Item 3 verificável por string em `test_components.py`, sem Chromium. |
| heading da região SCPI (anexo #167) | **procede — maior que a issue diz.** `preview_importacao_scpi.html:163-462` (ramo de resultados) sem `<h2>` de região **nem** de cartão — cada `<article>` de linha usa `<code>` como título (`:347`), divergindo do padrão de cartão (`design-system.md:1119`, testado em `test_views.py:2854/3282` com `<h2>`). O `<h2 sr-only>` removido na #167 nomeava a legenda, não os resultados. | `<h2 class="sr-only">` de região + `<h2>` por cartão. `sr-only` já no `app.css`. Caso novo na lane `navegador` (`get_by_role("heading")`). |
| CTA "Ver as N divergências" rolando ~40px | fora do escopo de a11y/markup; já há branch `upstream/fix/estoque-recorte-ancora-preview-scpi`. | Não entra nesta fatia. |
| `home()` do chefe cai na fila de atendimento | decisão de produto (issue mesma marca "não é markup"). | **Sai da fatia.** Candidato a issue própria se o chefe confirmar o destino desejado. |
| `/login/` sem rota de recuperação de senha | depende de haver canal de recuperação definido — produto. | **Sai da fatia.** Bloqueado por decisão de produto. |
| duas gramáticas de identificador sem badge de origem (`001.001.001`×`MAT-001`) | feature, não defeito de markup. | **Sai da fatia.** Candidato a issue própria (feature de catálogo). |

Todos os 4 itens acionáveis exigem **teste novo** — nenhum tem cobertura na lane `navegador` hoje. `make test-navegador` é gate obrigatório declarado no corpo.

**A #184 na prática — 4 itens procedem, decisão da normalização SCPI travada (2026-09-09).**

| Item da issue | Veredito da análise | Decisão |
|---|---|---|
| rótulo de rota × tela | **procede.** nav `'Fila de autorizações'`/`'Atendimento'` (`core_tags.py:731/749`) × página `Fila de autorização`/`Fila de atendimento` (`fila_*.html:4,7`). Regra #160 (`CONVENTIONS.md:295`) = nav segue destino; testada só p/ histórico SCPI (`test_views.py:2281`). **`test_views.py:2109` (`'Fila de atendimento' in html`) quebra** se o H1 virar "Atendimento". | nav segue a página (regra #160): nav → "Fila de atendimento" e "Fila de autorização". Ajustar `NAVEGACAO` + o teste que blinda. Estender a cobertura de `test_h1_e_title_repetem_o_rotulo_da_navegacao` às duas filas. |
| grafia "WMS SAEP" × "WMS-SAEP" | **procede.** `login.html:16` é o **único** outlier do repo (~27 usos com hífen, incl. `login.html:4`). **`test_login.py:32` (`assert 'WMS SAEP' in conteudo`) trava a grafia errada** — muda junto. | Padronizar em `WMS-SAEP`. Corrigir template + teste. |
| CAIXA ALTA do SCPI | **procede (mecanismo).** `services.py:746` grava `nome=linha.denominacao_scpi or linha.cadpro`; parse (`selectors.py:181`) só `.strip()`. Zero normalização em qualquer camada. Único `Material.objects.create` do código é a importação; seed nasce sentence case (`seed_dev.py:86`). Detalhe do `<ul>` no corpo está errado (é grid de `<article>`, `lista_materiais.html:53`). Regra da Caixa Alta (`DESIGN.md:322`) é redigida como regra **tipográfica** — estender a "dado que chega maiúsculo" é leitura esticada mas razoável. 13 pontos de exibição de denominação, nenhum com `\|capfirst`/`\|title`. | **Normalizar NA ESCRITA** (decisão do usuário, 2026-09-09). Helper novo em `apps/core/texto.py` chamado na criação do `Material` em `services.py`. **Nota de rename:** este registro histórico dizia `apps/core/texto.py::sentence_case`; o helper foi criado com esse nome e **renomeado para `capitalizar_frase` no PR #192** (achado BAIXA do `revisor-camadas` — identificador em inglês destoava dos helpers PT-BR de `apps/core`). Divergência doc↔código do dia 09 corrigida aqui: o nome vivo é `capitalizar_frase`. Ambiente efêmero (ADR-0009) → sem data migration, `make setup` materializa. `ordering=('nome',)` → `Lower('nome')` avaliado e **descartado** no PR (escrita normalizada já dá ordenação estável). Evitar `\|title` do Django (quebra `3/4"`, `280G`) e `capfirst` sozinho (não resolve ALL-CAPS no meio). Razão no PR. |
| asterisco de obrigatório no login não discrimina | **procede.** `login.html:40-41` inclui `form_field.html` sem `required_marker`; os 2 campos herdam `required` de `AuthenticationForm`. `DESIGN.md:554`: o asterisco é o único indicador de obrigatoriedade — com 100% obrigatório, vira ruído. Sem teste guardando. | Suprimir o asterisco quando todos os campos do form são obrigatórios (ou marcar os opcionais, invertendo a convenção só nessa tela). Definir na implementação. |

**A #185 na prática — a análise re-triou 2 dos ~5 itens (2026-09-09).**

| Item da issue | Veredito da análise | Decisão |
|---|---|---|
| `font-mono` indocumentado | lacuna real. 11 usos em templates (só `apps/estoque/`), +2 que a issue não cita (`detalhe_saida_excepcional.html:79`, `_alert_sucesso_importacao_corpo.html:45`). `--font-mono` **nem está no `@theme` do `input.css`** — vem do default do Tailwind v4. | Doc em DESIGN.md §Typography + design-system.md §Tipografia; declarar `--font-mono` explícito no `input.css` ⇒ `make css-build`. |
| exceção do `grid-cols-2` | parcial. `historico_movimentacoes.html:141` é `grid grid-cols-2` fixo num `<dl>` de cartão de listagem, contra a consequência explícita da "Regra da Identidade Que Não Quebra" — mas o código (`06b88d5`, #163) é **1 dia anterior** à regra (`abbd109`), e há **2ª ocorrência fixa** em `requisicoes/detalhe.html:132` (fora de listagem). A regra vive só no DESIGN.md, nem é citada no índice de regras nomeadas de `design-system.md`. | Registrar como exceção consciente (dado numérico curto, sobrevive a 295px, feito de propósito). Sem mudar template. Nota da 2ª ocorrência. |
| `ConflitoDominio` em âmbar | **premissa errada.** O mapa `→ severity='warning'` é **canônico**: `CONVENTIONS.md:201`, ADR-0011 Emenda `:246`, e travado por 4+ testes (`test_presentation.py:39`, `estoque/tests/test_views.py:611,997` — docstring *"Drift 6 (canônico): ... nunca messages.error"*). `DESIGN.md:232` **lista literalmente** "saldo insuficiente inline" como uso válido do âmbar. `SaldoInsuficiente`/`MaterialInativo`/`SaldoDivergente` **não são classes** — são `code=` em `ConflitoDominio` levantada de `apps/estoque/services.py`. | **Item fechado — premissa contradita pela própria doc.** Em vez disso: limpar o texto original do ADR-0011 `:70-72` (ainda diz `ConflitoDominio → error`) marcando-o `> Substituído pela Emenda de 2026-06-26`, alinhando com as outras revogações do arquivo (`:110-112`, `:146-148`). |
| gramática de formas | lacuna real, **pré-requisito da #172**. §Shapes só cobre border-radius por superfície. `danger` (`alerta.svg`) e `info` (`informacao.svg`) usam o **contorno circular idêntico** (`M18 10A8 8 0 1 1 2 10a8 8 0 0 1 16 0Z`) — só o miolo muda (! vs i). `design-system.md:461/463` os chama "círculo de informação"/"círculo de alerta" fingindo distinção geométrica. Sem regra "cada nível de feedback tem forma própria". Registry `{% icon %}` / `components/icons/` não documentado como parte do design system. | Doc: inventário das 3 silhuetas, a colisão `danger`≈`info` declarada como **dívida conhecida** (ancora a #172), regra pílula×retângulo, regra chip×badge. |
| anexo #167 — chip × badge | colisão real. Chip ativo (`filter_chips.html`) e `badge.html variant="blue"` = mesmo `bg-primary-muted` + `text-primary-text-strong` + `rounded-full`; diferem em contorno (`border` vs `ring`), padding, peso, `min-h-11`, glifo `✕`. `filter_chips.html` incluído por **3 telas** (`historico_requisicoes`, ledger `historico_movimentacoes`, `preview_importacao_scpi`) — as 3 rendam badge azul. `filter_presets_periodo.html:27` usa string **idêntica** à do chip ativo. **Zero teste** afere as classes do chip (badge tem teste por variante — assimetria). Chip **já tem** `focus-visible` canônico (não é alvo da #186). "11 telas da #166" = custo de regressão do gate, não 11 telas com chip (só 2 das 11 têm). | **Decisão: diferenciar o chip** (é o elemento com o defeito de affordance — quem age deve parecer acionável). Regra nova em DESIGN.md + ajuste em `filter_chips.html` (e `filter_presets_periodo.html`). `make test-navegador` obrigatório. Novo teste de classes do chip. |

Correção de bullet já registrada: contadores (`5 linhas`, `rounded-lg px-4 py-2.5`) e chips (`rounded-full`) **não** colidem — já se distinguem por forma. Sai da #173 (era premissa falsa do corpo original).

**Achados de review da #189 (2026-09-09, `joaorighetto`, 2× 🟡):**

1. **Guarda de `--font-mono` era teatro** (`test_tokens_semanticos.py`). `assert '--font-mono' in conteudo` passava com menção em comentário — e o próprio bloco de comentário do `@theme` cita a família 3×. O teste do `app.css` era tautologia: o default do Tailwind sempre emite `--font-mono`, então passaria em `main`, antes do PR. Corrigido (`7364cd0`): `_corpo_theme_sem_comentario` remove comentários CSS e isola o corpo do `@theme`; regex exige a declaração `--font-mono: <valor>;`; controle negativo sintético (`test_entrada_sintetica_font_mono_so_no_comentario_e_reprovada`) prova que o guarda morde. Padrão vizinho: `frontend_step_nao_e_validacao` — restrição fora do caminho de escrita não valida.
2. **Contradição na regra de forma** (`DESIGN.md`). `rounded-full` = "marcador estático" mas a lista incluía o botão-ícone da barra, que é acionável. Corrigido (`87e52d4`): o eixo deixou de ser acionável×estático e virou **rótulo textual × sem rótulo**. Controle com rótulo → `rounded-md`; ação circular icon-only → pílula, nomeada como exceção que §Shapes:447 já reservava.

Os dois threads foram respondidos com o SHA e resolvidos via GraphQL.

**Achados do CodeRabbit na #189 (2026-09-09, disparado manual — repo <10 stars não recebe auto-review; 2× 🟡):**

3. **`input.css:39` — Stylelint `value-keyword-case`** em `SFMono-Regular`/`Menlo`/`Monaco`/`Consolas`. **Declinado** (`3971371189`): o projeto não tem Stylelint (sem config, sem dep, sem job de CI — o pipeline de CSS é só `make css-build`); o valor é cópia verbatim do default do Tailwind v4, que é o propósito do PR; são nomes próprios de família de fonte, não keywords.
4. **Medição ausente nas regras novas do `DESIGN.md`** — o `.coderabbit.yaml` tem path instruction para `DESIGN.md` exigindo "a medição que justifica" cada regra nomeada. Corrigido (`44527d2`): (a) exceção do `grid-cols-2` em `requisicoes/detalhe.html:132` ganhou a medição a 375px (~295px de contêiner via `p-6`+`p-4`, ~140px/célula, número `whitespace-nowrap`, unidade/justificativa quebram em altura sem estouro); (b) a regra pílula×raio-de-controle foi marcada como taxonomia (não medição de viewport) com evidência = precedente §Paridade + colisão de classe verificável `filter_chips.html`≈`badge.html blue`; (c) `docs/design-system.md` alinhado. LanguageTool (vírgula após travessão, repetição) resolvido na reescrita.

Nota durável: **guardas de teste que fazem substring match em arquivo com comentário são teatro** — mesma classe de `frontend_step_nao_e_validacao`. O `.coderabbit.yaml` deste repo tem path instructions fortes (services/policies/selectors/DESIGN.md com regras próprias) — vale ler antes de mexer nessas superfícies.

**⚠️ A topologia de remotes mudou em 2026-09-08, por decisão do usuário.** PRs passam a
nascer no **`origin`** (`JMZR-SAEP/WMS-SAEP-v2`), o mesmo repo das issues; o fork
`joaozuneda6` sai do fluxo. A PR #188 validou: push + `gh pr create --repo JMZR-SAEP/...`
de primeira, conta com permissão ADMIN.

**Consequência que apaga uma regra inteira deste documento:** `Closes #N` agora vincula
de verdade (`closingIssuesReferences` confirmou a #187 ligada à #188). O merge fecha a
issue sozinho — a regra "merge não fecha issue de outro remote", que cobrou quatro
rodadas, deixa de valer. Some também o passo de sync `push origin upstream/main:main`.

**Contrapartida:** o CodeRabbit não revisa no `origin`. O check aparece **`pass`** com
`Review skipped: manual review required for this OSS repository` — verde sem review
nenhum. O gate de review que motivava o fork **não existe mais no fluxo**; revisão passa
a ser humana. Ver `project_coderabbit_inactive_and_stacked_merge`.

**A #187 na prática — três dos seis itens estavam mal diagnosticados na issue.** A análise (3 `Explore` em paralelo, read-only) desmentiu o corpo antes de qualquer linha de código:

| Item | O que a issue dizia | O que era |
|---|---|---|
| `motivo` slug | "falta `get_motivo_display`" | o método **não existia**: campo era `TextField` **sem `choices`**, vocabulário morava em lista literal do form. Conserto = mover choices ao model ⇒ vira **peça de schema**. E o defeito era **par**: `detalhe_` e `lista_saidas_excepcionais.html` |
| `IntegerField` | peça de schema | é **`forms.IntegerField`** (`requisicoes/forms.py:109`) — **não toca schema**. Nenhum campo de quantidade do domínio é inteiro; o padrão é `DecimalField(12,3)` em 11 campos. Reincidia em `views.py:510` com `int()` truncando decimal já gravado |
| ordenação | "exibe o inverso do que mostra" | `order_by` e `aria-label` **corretos**; só a **seta** contradizia. Decisão de vocabulário visual, não bug de dado |
| `@drop` | 1 ocorrência | **duas** — `:25` e `:243` (`onchange`). E `.submit()` também pula validação de `required`, o que a issue não registra |
| unidade do SCPI | schema (correto) | **barato**: `LinhaPreviewSCPI` já carrega `unidade`; o service a descartava no `bulk_create`. Zero consulta nova |
| `Doação` | 1 linha (correto) | confirmado: zero migration, zero seed, zero teste |

**Decisões tomadas nesta rodada:**

1. **O drop passa a só selecionar, não enviar.** A copy da tela já decidia: *"Arraste o arquivo aqui ou clique para selecionar"*. Sem `.submit()` programático as duas falhas somem juntas — guarda de duplo envio, rótulo de carregamento e validação de `required` voltam a valer no único caminho de envio.
2. **A seta nomeia o estado corrente; o texto segue nomeando o destino.** Respondem a perguntas diferentes ("onde estou" × "para onde vou"). O comentário do componente explicava o texto e silenciava sobre a seta — que era a metade errada.
3. **`motivo` sem migração de dados.** Ambiente efêmero (ADR-0009), sem base a preservar. Fixtures que gravavam texto livre passam ao slug, que é o que o form sempre produziu.
4. **`step` do campo numérico é calculado no servidor** e viaja no payload do autocomplete. Calculá-lo em JS criaria segunda tabela de unidades, livre para divergir de `apps/core/quantidades.py`. O cliente aplica, não decide.
5. **Resíduo declarado:** `_delta_movimentacao.html` usa a unidade para a precisão mas **não imprime o símbolo** — decisão do átomo, compartilhada com o histórico de movimentações. Mudá-la arrastaria as 11 telas da varredura da #166. Fica fora da fatia, como o chip que foi para a #185.

**Armadilha de template reincidente:** usei `{# … #}` multi-linha e o guard `test_nenhum_template_usa_comentario_de_linha_em_varias_linhas` pegou. A memória `project_guards_template` já registrava. Dentro de tag HTML aberta, `{% comment %}` funciona.

**Decisões desta rodada, que mudaram o escopo do que as issues pediam:**

1. **#167 fechou por remoção.** A issue pedia alinhar o shade dos swatches e acrescentar a linha do estado `OK`. Ao ler a tela inteira: são **três** cores por estado (cartão `-subtle`, badge `-muted`, swatch `-muted`), e o swatch batia com o badge, não com o cartão. Pior, acrescentar a linha `OK` sob o alinhamento pedido exigiria um swatch `bg-surface` — quadrado branco invisível, o mesmo modo de falha que a #164 diagnosticou. E a legenda **duplicava os chips**: explicava exatamente o par que `Só divergências` e `Só materiais novos` já nomeiam poucas linhas acima. Argumento que fechou: todo badge da tela é **texto**, e legenda existe para decodificar sinal não-textual.
2. **A L89 governa o marcador do catálogo, não um painel.** A observação da L89 ("Gestão do Almoxarifado/suporte") é o nome da L96, e a L96 nega ao auxiliar o que a L89 concede. Sob a leitura do painel, a L89 seria permissão morta para o auxiliar de almoxarifado — e nenhum painel existe no código. Decidido: é o marcador.
3. **#178 esconde o badge E os operandos.** EST-07 é `físico < reservado`, e o cartão imprimia os dois lados sem gate: esconder só o booleano removeria o rótulo, não a informação. `Disponível` fica para todos (L72), com resíduo declarado — num material divergente ele é negativo, e a L71 já bloqueia a seleção desse material por desenho.
4. **#181 mantém o 404, não adota o 403.** ADR-0010:118 (404 por não-enumeração) e ADR-0011 (`PermissaoNegada` → 403) colidem exatamente neste caso. Notificação de terceiro é objeto fora do escopo de visibilidade, então o 404 vence: um 403 confirmaria a existência da notificação a qualquer autenticado. Substituição explícita e comentada, que a emenda da ADR-0011 autoriza.
5. **Policy nova sem par `exigir_pode_*`, de propósito.** `pode_consultar_divergencias_criticas` não guarda endpoint — só decide escopo de conteúdo. Criar um `exigir_*` sem chamador plantaria de novo o defeito que a #181 existe para consertar.
6. **Estilo de selector escopado: `ator_id` + `papel_efetivo` interno.** O repo tem dois padrões vivos e nenhuma ADR decide. Escolhido o do vizinho direto (`movimentacoes_visiveis_para`), cujo padrão a matriz §5 L107 já ratifica. A nota nova do `CONVENTIONS.md` (PR #70) descreve esse padrão.

**Restrição de ambiente descoberta na rodada:** worktrees paralelos **não** servem aqui. O banco é PostgreSQL único e `make resetpostgres` apaga o schema `public`; duas suítes pytest simultâneas colidem em `test_<dbname>`, e migrations são gitignored, então worktree novo exige `make setup`, que reseta o banco compartilhado. Paralelismo vai na **análise** (read-only, sem branch, sem DB); implementação é sequencial.

**Decisões de domínio da #176 (2026-09-04).** A metade 2 não era divergência matriz↔código: `pode_visualizar_preview_scpi = eh_superusuario` batia com `docs/matriz-permissoes.md` L85-87. O conflito era matriz ↔ `PRODUCT.md:44` + `docs/processos-almoxarifado.md:88-96`. Resolvido:
1. Preview SCPI → **chefe de almoxarifado** (superusuário mantém override). Feito no #63.
2. Confirmar SCPI → **chefe também** (preview + confirmar + tela de sucesso). Feito no #63.
3. Matriz L89 "divergências críticas" = **invariante EST-07** (`físico < reservado`), não divergência SCPI → `divergente_calculado` (`selectors.py:324-328`) vaza o marcador para todo usuário ativo. Virou **#178**.
4. Inativar material → matriz L74/§3 já concede ao chefe, mas `pode_gerir_catalogo` só é consumida pelo admin do Django e não há UI de produto. **Tirado do #63** (mudar só a policy = código morto). Virou **#180**.
5. Matriz L83 "Estornar devolução" sem policy nem service → virou **#179**.

Nota factual: a policy real é `apps/estoque/policies.py:56`, não `apps/accounts/policies.py:56` como a issue diz.

**Spinoffs da #176 — triados, onda 5**

| # | O quê | Label | Bloqueio |
|---|---|---|---|
| 178 | `divergente_calculado` expõe o marcador EST-07 a solicitante/aux. setor/chefe setor (matriz L89) | `ready-for-agent` | — |
| 179 | `pode_estornar_devolucao` + service — linha de matriz (L83) sem implementação | `ready-for-agent` | **shape completo 2026-09-10** — 1 decisão bloqueante: estorno por quantidade-contra-agregado (A, recomendada) vs model `Devolucao` próprio (B). |
| ~~180~~ | inativar material só existe pelo admin do Django; decidir UI de produto ou recuar a matriz | **fechada** (`JMZR-SAEP#200`, merge `3230f34`) | — |

**Spinoffs da #166 — triados, onda 5.** Achados pela auditoria de papéis que escolheu o usuário de cada tela do parametrize. Nenhum é vazamento de autorização hoje; os dois são defeito de contrato.

| # | O quê | Label | Bloqueio |
|---|---|---|---|
| 181 | `pode_ver_notificacao` é policy órfã: sem consumidor de produção, a regra vive no filtro de ORM da view (ADR-0011 existe para evitar as duas fontes) | `ready-for-agent` | — |
| 182 | `listar_saidas_excepcionais(ator_id)` ignora o parâmetro — assinatura simula recorte por papel que não existe | `ready-for-agent` | — |

**Spinoff da #181 — aberto 2026-09-08**

| # | O quê | Label | Bloqueio |
|---|---|---|---|
| 183 | contagem do sino em `except Exception` com fallback zero, em toda página autenticada — zero é indistinguível de "nada pendente". Mesma classe de defeito que a #175 consertou. | `ready-for-agent` | — |

**Spinoffs da #186 — abertos/identificados 2026-09-09 na análise**

| # | O quê | Label | Bloqueio |
|---|---|---|---|
| ~~190~~ | footer de TODO modal (`_modal_body.html`): `flex-col-reverse` fazia a ordem de foco contradizer a visual a `<640px`. **Fechada** — PR `JMZR-SAEP#193`, merge `50e1d36`. | ~~`ready-for-agent`~~ | — |
| — | `home()` do chefe de almoxarifado cai na fila de atendimento. Decisão de produto (destino desejado). | (a abrir) | resposta do chefe |
| — | `/login/` sem rota de recuperação de senha. Depende de canal de recuperação definido. | (a abrir) | decisão de produto |
| — | catálogo mistura `001.001.001` (SCPI) e `MAT-001` (WMS) sem badge de origem. Feature de catálogo. | (a abrir) | — |

**Aberto — todas triadas (nenhuma `needs-triage` restante). A onda 6 é a #173 fatiada em quatro**

| # | Onda | Label | Bloqueio |
|---|---|---|---|
| ~~187~~ | 6 | **fechada** (`JMZR-SAEP#188`, merge `d2db3b3`) — fatia (d) da #173 | — |
| ~~185~~ | 6 | **fechada** (`JMZR-SAEP#189`, merge `11a6d65`) — fatia (b) da #173 | — |
| ~~186~~ | 6 | **fechada** (`JMZR-SAEP#191`, merge `a47184a`) — fatia (c) da #173 | — |
| ~~184~~ | 6 | **fechada** (`JMZR-SAEP#192`, merge `08972ac`) — fatia (a) da #173 | — |
| ~~190~~ | — | **fechada** (`JMZR-SAEP#193`, merge `50e1d36`) — spin-off de #186, footer de todo modal, WCAG 2.4.3 | — |
| ~~173~~ | 6 | **fechada** (auto-close via #192) — guarda-chuva, onda 6 completa | — |
| 194 | 7 | `ready-for-agent` | — (prioridade 1 da onda 7; começa com shape/Plan) |
| 195 | 7 | `ready-for-agent` | — (depois da #194) |
| 196 | 7 | `ready-for-agent` | — |
| 197 | 7 | `ready-for-agent` | — |
| 198 | 7 | `ready-for-agent` | — |
| 172 | 8 | `ready-for-human` (decisão de vocabulário visual) | **destravada** — #185 documentou a gramática de formas |
| 170 | 9 | `ready-for-agent` | **destravada** (2026-09-10) — decisão: recusar⇒rascunho, cancelar⇒anular, proibido pós-entrega. Precisa shape. |
| 171 | 10 | `ready-for-agent` | **destravada** (2026-09-10) — CSV real anexado. Próximo: medir o arquivo. |
| 169 | 11 | `needs-info` | medição da rede do piloto |
| 174 | 12 | `ready-for-human` (decisão de contrato, maior item) | — |
| 179 | — | `ready-for-agent` | **shape completo** (2026-09-10) — falta decisão A/B (quantidade-contra-agregado vs model `Devolucao` próprio), escalada ao usuário. |
| ~~180~~ | — | **fechada** (`JMZR-SAEP#200`, merge `3230f34`) — inativar/reativar material, UI de produto | — |

## Ordem de ataque

1. ~~**#176, metade barata** — `home()` para de rotear por `is_superuser`.~~ **Feito e fechada — PR #62.**
2. ~~**#168** — mover `input.css`, apagar `apps/core/staticfiles.py`.~~ **Feito e fechada — PR #65** (squash `c3f7fb1`).
3. ~~**#177** — 4 variantes cruas de `badge.html`.~~ **Feito e fechada — PR #66** (squash `0ee1949`, empilhada sobre a #65, retargetou pra `main` sozinha ao mergear a #65).
3b. ~~**`quantidade.html`**~~ **Feito e fechada — PR #68** (merge `421ce15`, sem CodeRabbit).
3c. ~~**#166**~~ **Feita e fechada — PR #69** (merge `95e8018`). Emendou a ADR-0019 no caminho.
4. ~~**#167**~~ **Feita e fechada — PR `joaozuneda6#71`** (merge `43b6dee`). Fechada por remoção da legenda. O bullet das pílulas do #173 **não** entrou: a premissa dele estava errada (ver "Candidatos"), e a colisão real precisa de mudança no componente global.
5. ~~**#178, #181, #182**~~ **Feitas e fechadas — PRs `joaozuneda6#72`, `#73`, `#70`.** Não houve conflito de hunk entre #178 e #182, apesar de editarem o mesmo `selectors.py`: as regiões eram disjuntas (20-27 vs 304-338; testes 9-78 vs 467-549). A #178 gerou a #183.
5b. ~~**#183**~~ **Feita e fechada — PR `joaozuneda6#75`** (merge `46ee10c`).
6. ~~**#173, fatiada em 3**~~ **Fatiada em 4: #184 (a), #185 (b), #186 (c), #187 (d).** A quarta fatia existe porque cinco dos candidatos anexados não eram achado estético e sim **defeito de comportamento** — diluí-los em (a)/(b)/(c) enterraria bug sob revisão de copy. **~~#187~~ fechada (PR #188). ~~#185~~ fechada (PR #189). ~~#186~~ fechada (PR #191, `a47184a`).** **~~#184~~ fechada (PR #192, `08972ac`) → #173 fechada. ~~#190~~ fechada (PR #193, `50e1d36`).** **A onda 6 e todos os seus spin-offs estão fechados. A fila de agente está vazia.**
7. **Onda 7 (critique rodada 3): #194 → #195 → #196/#197/#198.** `ready-for-agent`. #194 é a prioridade (decisão do usuário) e o maior item — vazão de fila, começa com shape/Plan. #195 é cirúrgico (só UI + `acoes_disponiveis`). #196/#197/#198 independentes entre si, sequenciais só pelo banco. Implementação sempre sequencial (banco PostgreSQL único).
8. **#172** — destravada (a #185 documentou a gramática de formas). `ready-for-human`.
9. ~~**#176, metade de permissão** — quem é o dono da importação SCPI.~~ **Feito e fechada — PR #63.** Domínio decidiu: chefe de almoxarifado. Gerou #178, #179, #180.
10. **#170** — destravada 2026-09-10. Shape: recusar⇒rascunho, cancelar⇒anular (criador/chefe), gate de entrega. Roda fora da fila da onda 7.
11. **#171** — destravada 2026-09-10, CSV real anexado. Medir o arquivo; cada quebra vira issue própria. Não ocupa slot de implementação.
12. **#179** — shape completo 2026-09-10. Falta decisão A/B (quantidade-contra-agregado vs model `Devolucao`) antes de abrir branch.
13. ~~**#180**~~ **Feita e fechada — PR `JMZR-SAEP#200`** (merge `3230f34`, 2026-09-10). Policy + service (`reativar_material`) + UI em `lista_materiais.html` + testes. 2 achados reais do CodeRabbit corrigidos num segundo commit (saldo inicial ausente sem estoque ativo; harness de contrato de modal sem prova de mutação em `muta=True`).
14. **#169** — medir a rede do piloto e decidir. `wontfix` consciente é o desfecho provável.
15. **#174** — a maior. Primeira a cortar do escopo se o piloto apertar.

## Dependências

- **#168 → #166, #177.** Os três editam `test_tokens_semanticos.py`. A #168 mexe na constante `INPUT_CSS`; as outras duas acrescentam cobertura. Fora de ordem = conflito garantido.
- **#177 ≡ #166 em forma.** Cor que existe, par que existe, guarda que não alcança — uma por paleta crua, outra por par pai/filho. Entender o guarda duas vezes é desperdício.
- ~~**#166 → #167, #173, #174.**~~ **Satisfeita.** A varredura está no lugar: toda mudança de markup daqui em diante nasce medida, nas 11 telas cobertas.
- ~~**#173 ⊃ #167.**~~ **Resolvida por medição**: o bullet das pílulas era falso (ver "Candidatos"), e a colisão real foi para a **#185**, que toca `filter_chips.html` — componente global que arrasta as 11 telas da varredura da #166.
- ~~**#185 → #172.**~~ **Satisfeita** — a #185 (merge `11a6d65`) documentou a gramática de formas no `DESIGN.md`. A #172 está livre para acontecer quando o humano decidir o vocabulário visual.
- **#187/#185 antes de #184/#186.** Feito. #186 antes de #184 é severidade (comportamento antes de copy), não código — sem dependência de build entre as duas.
- **#176 se divide em duas metades independentes.** A do laço fechado é defeito puro e sai sozinha; a da policy espera decisão de domínio.
- **Sem dependência de código real entre as demais.** As dependências que importam neste backlog são de **informação** (respostas humanas) e de **contaminação de medição**, não de build.

## Trabalho sem issue própria

**Fechado e mergeado — PR `joaozuneda6/WMS-SAEP-v2#68`** (merge `421ce15`, sem CodeRabbit, merge manual do usuário). Os dois P1 vizinhos de `components/quantidade.html` (linha 60, `text-tertiary` reprovando contraste; linha 64, `tom` não propagava pra `referencia`) saíram no mesmo PR. Pull request criada com corpo corrompido por expansão de crase no shell (`` `tom` `` virou tentativa de comando) — corrigido via `gh pr edit --body-file`. Nota pra próxima vez: nunca passar `--body` inline com crases dentro de aspas duplas no bash; usar heredoc/arquivo.

## Candidatos do #173 — distribuídos em 2026-09-08

Todos os candidatos da remedição foram para uma fatia. Nada ficou sem dono:

| Candidato | Foi para |
|---|---|
| DELTA do SCPI sem unidade nas duas telas | **#187** — muda schema (`LinhaDivergenteSCPI`) |
| `motivo` gravado como slug no livro-razão imutável | **#187** |
| `Doação` num seletor que o `PRODUCT.md` declara fora de escopo | **#187** |
| `@drop` que submete sem revisão e mata o `data-prevent-double-submit` | **#187** |
| ordenação que exibe o inverso do que mostra | **#187** |
| `IntegerField` num material medido em metros | **#187**, por comentário — escapou do corpo no primeiro fatiamento |
| ordem de foco invertida (`flex-col-reverse`, WCAG 2.4.3) | **#186** |
| 12 links de navegação sem `focus-visible` autoral | **#186** |
| chip ativo × badge do cartão (achado da #167) | **#185** — `filter_chips.html` é global |
| heading ausente na região de resultados do preview (achado da #167) | **#186** |

**Duas peças de schema na #187**: a unidade do `LinhaDivergenteSCPI` e o `IntegerField`. Se a fatia crescer, elas se separam **juntas** — ambas mudam model e ambas exigem `make setup`.

**Correção de um bullet existente, medida na #167 (2026-09-08).** O bullet que diz que contadores (`5 linhas`) e filtros (`Só divergências`) vestem a mesma pílula a ~170px **não se sustenta**: os contadores são `rounded-lg` com `px-4 py-2.5` — retângulos, não pílulas — e os chips são `rounded-full`; já se distinguem por forma, e os três contadores se distinguem entre si por matiz. Os dois achados reais que o substituem:

- **Chip ativo × badge do cartão vestem a mesma pílula.** `filter_chips.html` no estado ativo usa `rounded-full border px-3 py-1.5 bg-primary-muted text-primary-text-strong`; `badge.html variant="blue"` usa `rounded-full bg-primary-muted px-2.5 py-0.5 text-primary-text-strong ring-1`. Mesma cor, mesma forma, diferindo só em tamanho. **Um é link que alterna filtro, o outro é marcador estático de estado** — é defeito de affordance, não de vocabulário. Ficou fora do escopo da #167 porque `filter_chips.html` é componente global (o ledger também o usa) e mexer nele arrasta as 11 telas da varredura de contraste da #166. Foi para a **#185**.
- **A região de resultados do preview SCPI não tem heading próprio.** Lacuna preexistente, não criada pela #167 — o `<h2 class="sr-only">` que saiu com a legenda nomeava a legenda, não os resultados. Um `<h2 class="sr-only">` para as linhas do arquivo daria a leitor de tela um alvo de salto para o conteúdo real da tela. Foi para a **#186**.

## Disparar cedo, fora da fila

Itens 8 e 9 têm lead time humano e **zero trabalho de código antes da resposta**. Mande os pedidos assim que a fila começar, e siga pelos itens 1 a 6 enquanto chegam:

- ~~**#176 metade 2** — quem é o dono da importação SCPI?~~ **Respondido: chefe de almoxarifado.** PR #63, issue fechada.
- ~~**#170** — "recusa" e "cancelamento" diferem?~~ **Respondido 2026-09-10:** sim, operações distintas. Recusar mescla com retornar-para-rascunho; cancelar é anular (criador ou chefe), proibido pós-entrega.
- ~~**#171** — export real do SCPI.~~ **Recebido 2026-09-10:** `todos_itens_cadastrados_de_marco_ate_setembro.csv` anexado na issue.
- ~~**#179** — estorno de devolução entra no MVP?~~ **Respondido 2026-09-10: Entra.**
- ~~**#180** — inativar material: UI de produto ou recuar matriz?~~ **Respondido 2026-09-10: UI de produto.**

## Regras de coordenação

- ~~**Não rode a próxima critique antes de fechar a onda 4.**~~ **Cumprida e vencida.** Rodada 3 rodou em 2026-09-10, depois da onda 6 fechada: 21 → 27 → **32/40**. A próxima só depois de a onda 7 (#194–#198) fechar, pela mesma razão de atribuição.
- **Comparação de nota só é válida like-for-like**: mesmo alvo, mesmo slug (`apps`), sem alvo específico, e sem mostrar a pontuação anterior aos agentes. Calibração diferente entre rodadas vira falso progresso ou falsa regressão. **Armadilha da rodada 3:** os dois agentes de assessment subiram o app na mesma porta e no mesmo banco de dev e colidiram — aba de browser e schema navegados concorrentemente. Um dos subagentes ainda rodou o fluxo `/critique` inteiro por conta própria e gravou um snapshot duplicado (removido). Próxima vez: um agente roda o app, o outro é só-fonte; e instruir explicitamente "não persista, não rode o fluxo".
- ~~**#173 é guarda-chuva, não issue.**~~ **Fatiada em #184/#185/#186/#187.** #185, #186 e #187 fechadas; fica aberta como capa até a **#184** fechar.
- ~~**Merge não fecha issue de outro remote.**~~ **Revogada em 2026-09-08**, quando os PRs passaram a nascer no `origin`. Com PR e issue no mesmo repo, `Closes #N` fecha a issue no merge — sem passo manual. O incidente das quatro issues abertas por quatro dias fica como histórico na seção "Ondas 4 e 5", não como regra ativa. **Vale só se algum PR voltar a nascer no fork:** aí o auto-close não cruza e o fechamento manual volta a ser obrigatório.
- **O gate de review mudou de dono.** O CodeRabbit responde no `origin` (validado na #188, 3 achados), mas o plano dá **1 review por hora** — e o check `CodeRabbit` pode aparecer `pass` com "Review skipped" sem ter revisado nada. Não confundir check verde com review feita; conferir se há comentários antes de tratar o gate como cumprido.
- **#169 e #171 não são tarefas de código** — uma medição da rede e a medição do CSV real. Não devem ocupar slot de implementação. (#170 **passou a ser** tarefa de código depois da decisão de 2026-09-10.)
- **#174 é dívida declarada com produção correta.** Primeira a sair do escopo sob pressão de prazo. A #168 fica só porque é barata.
- Uma branch por issue, nunca commit direto na `main`; vocabulário de triagem em `docs/agents/triage-labels.md`.

## Manutenção desta memória

Atualize quando: uma issue fechar, uma onda concluir, uma decisão externa chegar (permissões, vocabulário de auditoria, export SCPI), ou uma nova rodada de critique mudar a ordem. Não registre progresso parcial de PR nem saída de teste — isso vive no PR.

Memórias vizinhas: `project_git_remotes_topology` (onde issue e PR moram), `project_css_build_gate` (classe nova exige `make css-build`), `frontend/etapa2_feedback_backlog` e `frontend/etapa3_overlay_backlog` (backlogs de etapas anteriores).
