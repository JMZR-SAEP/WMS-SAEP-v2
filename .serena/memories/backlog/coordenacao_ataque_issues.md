# Coordenação do ataque às issues — backlog pós-Etapa 8

**Documento vivo.** Ponto de partida para quem entra no backlog e ferramenta de acompanhamento para quem já está nele. Visão macro: o detalhe técnico vive na issue, aqui vive a **ordem, a dependência e o estado**.

Última atualização: **2026-09-04**.

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

**Em andamento**

Nada em execução no momento. Próximo item desbloqueado: **#176, metade barata**.

**Aberto — 11 issues**

| # | Onda | Estado | Bloqueio |
|---|---|---|---|
| 176 | 1 | metade 1 pronta / metade 2 travada | decisão de matriz de permissões |
| 168 | 2 | pronta | — |
| 177 | 3 | pronta | — |
| 166 | 3 | pronta | vem depois de 168 e 177 |
| 167 | 4 | pronta | — |
| 173 | 5 | precisa ser fatiada | — |
| 172 | 6 | precisa de decisão de vocabulário visual | 173(b) documentar a gramática de formas |
| 170 | 7 | pergunta em aberto | resposta do chefe de almoxarifado |
| 171 | 8 | sem trabalho de código | export real do SCPI |
| 169 | 9 | triagem | medição da rede do piloto |
| 174 | 10 | precisa de decisão de contrato | — |

## Ordem de ataque

1. **#176, metade barata** — `home()` para de rotear por `is_superuser`. Duas linhas, sem esperar decisão nenhuma, desfaz um beco sem saída. Melhor retorno por linha de toda a fila.
2. **#168** — mover `input.css`, apagar `apps/core/staticfiles.py`. Mecânica, e **limpa `test_tokens_semanticos.py` antes dos dois PRs que vão editá-lo** (#166 e #177). Esta é a razão de ela subir na fila, não o valor próprio.
3. **#177 → `quantidade.html` → #166**, nesta ordem. O eixo do componente. A #177 é barata e obriga a decidir se as quatro variantes ainda existem; o PR de `quantidade.html` fecha os dois P1 sem issue (ver abaixo); a #166 vem por último e nasce medindo o que os anteriores acabaram de consertar.
4. **#167** — leve o bullet das pílulas do #173 no mesmo PR: mesma tela, mesmo arquivo.
5. **#173, fatiada em 3** — (a) copy e vocabulário; (b) `DESIGN.md`; (c) navegação e responsivo. Anexar os candidatos novos antes de abrir o primeiro PR.
6. **#172** — depois que 5(b) documentar a gramática de formas.
7. **#176, metade de permissão** — quando o domínio disser quem é o dono da importação SCPI.
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

Dois P1 da remedição que não viraram issue porque caem dentro de PRs já previstos. **Se o eixo do componente for reordenado, eles ficam órfãos — recupere-os aqui.**

- `components/quantidade.html:60` — `text-tertiary` reprova 4,5:1 em 3 das 7 superfícies do sistema. É a justificativa medida da #166.
- `components/quantidade.html:64` — `tom` não propaga para `referencia`, então o aviso "acima do saldo" sai no mesmo cinza do metadado. É o P0 da Etapa 8 entregue pela metade: o botão que vai falhar é 5,4× maior que o texto que diz que vai falhar.

Mesmo arquivo, linhas vizinhas: **um PR fecha os dois.**

## Candidatos a anexar ao #173

A remedição achou itens que não estão no bundle. Anexar antes de fatiar: DELTA do SCPI sem unidade nas duas telas; `motivo` gravado como slug no livro-razão imutável; `Doação` num seletor que o `PRODUCT.md` declara fora de escopo; `@drop` que submete sem revisão e mata o `data-prevent-double-submit`; ordenação que exibe o inverso do que mostra; `IntegerField` num material medido em metros.

## Disparar cedo, fora da fila

Itens 7, 8 e 9 têm lead time humano e **zero trabalho de código antes da resposta**. Mande os três pedidos assim que a fila começar, e siga pelos itens 1 a 6 enquanto chegam:

- **#176 metade 2** — quem é o dono da importação SCPI na matriz de permissões?
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
