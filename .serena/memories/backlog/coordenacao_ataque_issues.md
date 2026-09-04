# Coordenação do ataque às issues — backlog pós-Etapa 8

**Documento vivo.** Ponto de partida para quem entra no backlog e ferramenta de acompanhamento para quem já está nele. Visão macro: o detalhe técnico vive na issue, aqui vive a **ordem, a dependência e o estado**.

Última atualização: **2026-09-04** (#166 implementada, PR #69 aberta e aguardando merge — inclui emenda à ADR-0019; spinoffs #181/#182 abertos, needs-triage; #167 é a próxima da fila assim que a #69 mergear).

## Como usar

- Antes de pegar trabalho: leia o quadro de estado e a ordem de ataque; pegue o primeiro item desbloqueado.
- Ao fechar algo: mova a linha para "Concluído", atualize a onda e registre o que a conclusão desbloqueou.
- Não replique aqui o conteúdo da issue. Se você está copiando parágrafo de issue para cá, está no lugar errado.
- Issues e PRDs vivem em `JMZR-SAEP/WMS-SAEP-v2`; PRs e CodeRabbit no fork `joaozuneda6/WMS-SAEP-v2` (ver `project_git_remotes_topology`).

## Origem deste backlog

Tudo aqui nasceu da **Etapa 8** (auditoria de frontend do produto inteiro) e da sua remedição. Duas medições heurísticas, mesmo alvo, mesmo método dual-agent:

| Rodada | Data | Nota | P0 | P1 |
|---|---|---|---|---|
| Etapa 8, Fase 2 | 2026-09-01 | 21/40 | 1 | 3 |
| Remedição (#165) | 2026-09-03 | **27/40** | 2 | 2 |

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

**Em andamento**

- **#166** — PR `joaozuneda6/WMS-SAEP-v2#69`, aberta 2026-09-04, aguardando merge.
  - **A PR emenda a ADR-0019** — decisão durável, não progresso: 4º critério de admissão ("cascade resolvida e pipeline de cor"), e o gatilho de "~15 casos" dá lugar ao relógio, porque a lane já estava em 3,2× o teto sem nunca ter disparado revisão.
  - Fora do escopo, anexar ao fechar: `estoque:preview_importacao_scpi` não entrou (exige upload multipart), então o guarda nasce cego para o `bg-primary-subtle` que originou tudo.

**Decisões de domínio da #176 (2026-09-04).** A metade 2 não era divergência matriz↔código: `pode_visualizar_preview_scpi = eh_superusuario` batia com `docs/matriz-permissoes.md` L85-87. O conflito era matriz ↔ `PRODUCT.md:44` + `docs/processos-almoxarifado.md:88-96`. Resolvido:
1. Preview SCPI → **chefe de almoxarifado** (superusuário mantém override). Feito no #63.
2. Confirmar SCPI → **chefe também** (preview + confirmar + tela de sucesso). Feito no #63.
3. Matriz L89 "divergências críticas" = **invariante EST-07** (`físico < reservado`), não divergência SCPI → `divergente_calculado` (`selectors.py:324-328`) vaza o marcador para todo usuário ativo. Virou **#178**.
4. Inativar material → matriz L74/§3 já concede ao chefe, mas `pode_gerir_catalogo` só é consumida pelo admin do Django e não há UI de produto. **Tirado do #63** (mudar só a policy = código morto). Virou **#180**.
5. Matriz L83 "Estornar devolução" sem policy nem service → virou **#179**.

Nota factual: a policy real é `apps/estoque/policies.py:56`, não `apps/accounts/policies.py:56` como a issue diz.

**Spinoffs da #176 — abertos, `needs-triage`, sem onda**

| # | O quê |
|---|---|
| 178 | `divergente_calculado` expõe o marcador EST-07 a solicitante/aux. setor/chefe setor (matriz L89) |
| 179 | `pode_estornar_devolucao` + service — linha de matriz (L83) sem implementação |
| 180 | inativar material só existe pelo admin do Django; decidir UI de produto ou recuar a matriz |

**Spinoffs da #166 — abertos, `needs-triage`, sem onda.** Achados pela auditoria de papéis que escolheu o usuário de cada tela do parametrize. Nenhum é vazamento de autorização hoje; os dois são defeito de contrato.

| # | O quê |
|---|---|
| 181 | `pode_ver_notificacao` é policy órfã: sem consumidor de produção, a regra vive no filtro de ORM da view (ADR-0011 existe para evitar as duas fontes) |
| 182 | `listar_saidas_excepcionais(ator_id)` ignora o parâmetro — assinatura simula recorte por papel que não existe |

**Aberto — 8 waves + 3 spinoffs da #176 (tabela acima)**

| # | Onda | Estado | Bloqueio |
|---|---|---|---|
| 166 | 3 | **em PR (#69)**, aguardando merge | — |
| 167 | 4 | pronta — **próxima da fila** quando a #69 mergear | — |
| 173 | 5 | precisa ser fatiada | — |
| 172 | 6 | precisa de decisão de vocabulário visual | 173(b) documentar a gramática de formas |
| 170 | 7 | pergunta em aberto | resposta do chefe de almoxarifado |
| 171 | 8 | sem trabalho de código | export real do SCPI |
| 169 | 9 | triagem | medição da rede do piloto |
| 174 | 10 | precisa de decisão de contrato | — |

## Ordem de ataque

1. ~~**#176, metade barata** — `home()` para de rotear por `is_superuser`.~~ **Feito e fechada — PR #62.**
2. ~~**#168** — mover `input.css`, apagar `apps/core/staticfiles.py`.~~ **Feito e fechada — PR #65** (squash `c3f7fb1`).
3. ~~**#177** — 4 variantes cruas de `badge.html`.~~ **Feito e fechada — PR #66** (squash `0ee1949`, empilhada sobre a #65, retargetou pra `main` sozinha ao mergear a #65).
3b. ~~**`quantidade.html`**~~ **Feito e fechada — PR #68** (merge `421ce15`, sem CodeRabbit).
3c. ~~**#166**~~ **Implementada — PR #69**, aguardando merge. Emenda a ADR-0019 no caminho.
4. **#167** — leve o bullet das pílulas do #173 no mesmo PR: mesma tela, mesmo arquivo.
5. **#173, fatiada em 3** — (a) copy e vocabulário; (b) `DESIGN.md`; (c) navegação e responsivo. Anexar os candidatos novos antes de abrir o primeiro PR.
6. **#172** — depois que 5(b) documentar a gramática de formas.
7. ~~**#176, metade de permissão** — quem é o dono da importação SCPI.~~ **Feito e fechada — PR #63.** Domínio decidiu: chefe de almoxarifado. Gerou #178, #179, #180.
8. **#170** — quando o chefe de almoxarifado responder.
9. **#171** — quando o export real chegar. Cada quebra vira issue própria.
10. **#169** — medir a rede do piloto e decidir. `wontfix` consciente é o desfecho provável.
11. **#174** — a maior. Primeira a cortar do escopo se o piloto apertar.

## Dependências

- **#168 → #166, #177.** Os três editam `test_tokens_semanticos.py`. A #168 mexe na constante `INPUT_CSS`; as outras duas acrescentam cobertura. Fora de ordem = conflito garantido.
- **#177 ≡ #166 em forma.** Cor que existe, par que existe, guarda que não alcança — uma por paleta crua, outra por par pai/filho. Entender o guarda duas vezes é desperdício.
- **#166 → #167, #173, #174.** A varredura de contraste é a rede de segurança das edições de template seguintes. Toda mudança de markup feita depois dela nasce medida.
- **#173 ⊃ #167.** O bullet das pílulas do preview SCPI é o mesmo arquivo da #167.
- **#173(b) → #172.** Os bullets de `DESIGN.md` fixam a gramática que o triângulo vai estender. Documentar antes de acrescentar.
- **#176 se divide em duas metades independentes.** A do laço fechado é defeito puro e sai sozinha; a da policy espera decisão de domínio.
- **Sem dependência de código real entre as demais.** As dependências que importam neste backlog são de **informação** (respostas humanas) e de **contaminação de medição**, não de build.

## Trabalho sem issue própria

**Fechado e mergeado — PR `joaozuneda6/WMS-SAEP-v2#68`** (merge `421ce15`, sem CodeRabbit, merge manual do usuário). Os dois P1 vizinhos de `components/quantidade.html` (linha 60, `text-tertiary` reprovando contraste; linha 64, `tom` não propagava pra `referencia`) saíram no mesmo PR. Pull request criada com corpo corrompido por expansão de crase no shell (`` `tom` `` virou tentativa de comando) — corrigido via `gh pr edit --body-file`. Nota pra próxima vez: nunca passar `--body` inline com crases dentro de aspas duplas no bash; usar heredoc/arquivo.

## Candidatos a anexar ao #173

A remedição achou itens que não estão no bundle. Anexar antes de fatiar: DELTA do SCPI sem unidade nas duas telas; `motivo` gravado como slug no livro-razão imutável; `Doação` num seletor que o `PRODUCT.md` declara fora de escopo; `@drop` que submete sem revisão e mata o `data-prevent-double-submit`; ordenação que exibe o inverso do que mostra; `IntegerField` num material medido em metros.

## Disparar cedo, fora da fila

Itens 8 e 9 têm lead time humano e **zero trabalho de código antes da resposta**. Mande os pedidos assim que a fila começar, e siga pelos itens 1 a 6 enquanto chegam:

- ~~**#176 metade 2** — quem é o dono da importação SCPI?~~ **Respondido: chefe de almoxarifado.** PR #63, issue fechada.
- **#170** — "recusa" e "cancelamento" diferem no vocabulário de auditoria do almoxarifado?
- **#171** — alguém com acesso ao SCPI produzir um export real.

## Regras de coordenação

- **Não rode a próxima critique antes de fechar a onda 4.** Rodar no meio mistura o efeito dos P0 com o do eixo do componente — o erro de atribuição que a #165 existia justamente para não repetir.
- **Comparação de nota só é válida like-for-like**: mesmo alvo, mesmo slug (`apps`), sem alvo específico, e sem mostrar a pontuação anterior aos agentes. Calibração diferente entre rodadas vira falso progresso ou falsa regressão.
- **#173 é guarda-chuva, não issue.** Fatiar antes de pegar.
- **#169, #170 e #171 não são tarefas de código** — são uma medição, uma pergunta e um pedido. Não devem ocupar slot de implementação.
- **#174 é dívida declarada com produção correta.** Primeira a sair do escopo sob pressão de prazo. A #168 fica só porque é barata.
- Uma branch por issue, nunca commit direto na `main`; vocabulário de triagem em `docs/agents/triage-labels.md`.

## Manutenção desta memória

Atualize quando: uma issue fechar, uma onda concluir, uma decisão externa chegar (permissões, vocabulário de auditoria, export SCPI), ou uma nova rodada de critique mudar a ordem. Não registre progresso parcial de PR nem saída de teste — isso vive no PR.

Memórias vizinhas: `project_git_remotes_topology` (onde issue e PR moram), `project_css_build_gate` (classe nova exige `make css-build`), `frontend/etapa2_feedback_backlog` e `frontend/etapa3_overlay_backlog` (backlogs de etapas anteriores).
