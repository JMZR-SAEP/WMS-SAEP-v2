# Auditoria de UI/UX — Sistema de Requisições SAEP

**Data:** 02/07/2026
**Escopo:** fluxo completo rascunho → autorização → atendimento → separação → retirada, incluindo o módulo de Histórico de Requisições e Notificações.
**Papéis testados:** Solicitante (OBRAS003), Auxiliar de setor (OBRAS002), Chefe de setor (OBRAS001), Auxiliar de almoxarifado (ALMOX002), Chefe de almoxarifado (ALMOX001).

---

## Metodologia

1. Leitura dos briefs de design existentes (`.design/telas-operacionais`, `.design/detalhe-requisicao`, `.design/topbar`, `.design/INFORMATION_ARCHITECTURE.md`, `.design/TASKS_REMEDIATION.md`) para estabelecer a linha de base de comportamento esperado.
2. Massa de dados de teste criada via camada de serviço (`apps/requisicoes/services/*`) cobrindo os 8 estados do ciclo de vida (rascunho, aguardando autorização, recusada, autorizada, pronta para retirada, atendida, cancelada, estornada), preservando os invariantes de domínio (nenhuma escrita direta em ORM).
3. Navegação end-to-end via Playwright MCP, autenticando com cada papel, em três breakpoints (375px mobile, 768px tablet quando relevante, 1280px desktop).
4. Inspeção de árvore de acessibilidade (`browser_snapshot`) para cada tela — mais confiável que inspeção visual para checar roles, labels, `aria-*` e ordem de foco.
5. Captura de screenshots (`.design/audit-uiux-2026-07/screenshots/`) para evidência visual e verificação de hierarquia/contraste/responsividade.
6. Leitura de código-fonte (templates, `selectors.py`, `forms.py`, `views.py`) para confirmar causa raiz de comportamentos suspeitos observados no browser, evitando reportar sintoma sem diagnóstico.
7. Cruzamento dos achados com `.design/TASKS_REMEDIATION.md` (rodada de QA anterior) para diferenciar regressões de itens genuinamente novos.

Servidor de desenvolvimento reaproveitado (processo já em execução, ambiente Postgres local via `.env`), sem alterações destrutivas — apenas inserção de requisições de teste via services.

---

## Achados

### Críticos

#### C1 — Histórico de requisições lista rascunhos de terceiros e gera link morto (404)
**O quê:** `historico_requisicoes_visiveis_para` (`apps/requisicoes/selectors.py:266`) filtra apenas por escopo de setor/papel, sem excluir `estado=RASCUNHO`. Como chefe de setor (OBRAS001), a tela `/requisicoes/historico/` lista o rascunho de um subordinado (OBRAS002) — dado que **nenhuma outra tela do sistema expõe** a esse papel. Clicar em "Ver" retorna **404**, porque a view de detalhe usa uma checagem de visibilidade mais restrita (rascunho só para o criador). A mesma linha exibe **"Rascunho #2"**, vazando o PK interno da requisição na coluna Número — contradiz diretamente a decisão já documentada em `detalhe-requisicao/DESIGN_BRIEF.md` (P3-01: *"PK interno não vaza para UI"*), que foi corrigida na página de detalhe mas não na tela de Histórico (feature mais recente, sem brief próprio).
**Impacto:** chefe/almoxarifado veem uma requisição no meio de uma consulta de histórico, clicam para investigar e caem em "página não encontrada" — quebra de confiança no sistema, e uma real exposição de trabalho em progresso alheio (rascunho é, por design, privado até o envio).
**Recomendação:** adicionar `~Q(estado=EstadoRequisicao.RASCUNHO)` (ou equivalente) ao queryset de `historico_requisicoes_visiveis_para`, espelhando a regra já aplicada em `requisicoes_visiveis_para`. Cobrir com teste de regressão.

Evidência: `screenshots/historico-desktop-1280.png`, `screenshots/historico-mobile-375.png`.

#### C2 — Formulário de atendimento não pré-preenche "Quantidade entregue" (quebra de fluxo mais comum)
**O quê:** ao abrir "Registrar retirada" (`/requisicoes/<id>/atender/`), o campo `Entregue` de cada item deveria vir pré-preenchido com a quantidade autorizada (fluxo majoritário: entrega total). Em vez disso, o campo aparece **vazio**. O console do browser confirma a causa: `The specified value "5,000" cannot be parsed, or is out of range`. O `DecimalField` do formset (`apps/requisicoes/forms.py:261`) usa `widget=forms.NumberInput`, e com `USE_I18N=True` + `LANGUAGE_CODE='pt-br'`, o Django formata o valor inicial com vírgula decimal ("5,000") — formato que o `<input type="number">` nativo **rejeita silenciosamente**, sem qualquer aviso visível ao usuário.
**Impacto:** o almoxarife precisa redigitar manualmente a quantidade de **cada item** em **toda operação de atendimento**, no fluxo de trabalho mais repetido do sistema. Risco de erro de digitação em campo que decide baixa de estoque físico. Falha silenciosa — nada na tela indica que o valor não carregou.
**Recomendação:** setar `localize=False` no `DecimalField` de `ItemAtendimentoForm` (ou formatar o `value` do widget manualmente com ponto decimal), garantindo que o pré-preenchimento use formato compatível com `type="number"`.

Evidência: `screenshots/atender-formulario-desktop.png` (campos "Entregue" vazios), console log com o warning.

#### C3 — Notificações expõem PK interna e não navegam até a requisição
**O quê:** todos os itens de `/notificacoes/` exibem `"Requisição #3"`, `"Requisição #11"` etc. — o PK numérico interno, nunca o número público (`REQ-2026-000003`). Além disso, o texto do item **não é um link**: a única ação disponível é "Marcar como lida". Não há caminho para ir da notificação até a requisição que a originou.
**Impacto:** duplo problema. (1) Vazamento sistemático de identificador interno em uma tela de alta visibilidade (o sino aparece com contador em **toda** página pós-login). (2) Quebra a expectativa mais básica de uma notificação — ser clicável — forçando o usuário a memorizar o número e ir buscar manualmente na lista correspondente.
**Recomendação:** trocar o rótulo para `numero_publico` (com fallback "Rascunho" quando nulo, consistente com o restante do sistema) e envolver cada item em link para `/requisicoes/<id>/`.

Evidência: `screenshots/notificacoes-desktop.png`.

---

### Altos

#### A1 — Validação de campo obrigatório usa tooltip nativo do browser, fora do design system
**O quê:** no modal "Recusar requisição?", submeter com o campo "Motivo da recusa" vazio dispara a validação HTML5 nativa (`required`) — um balão cinza do Chrome ("Preencha este campo.") sobre o textarea, em vez de uma mensagem de erro integrada ao design do modal (que já existe e é usado corretamente para erros vindos do servidor).
**Impacto:** quebra visual do design system customizado no momento exato em que o usuário mais precisa de clareza (correção de erro). Comportamento e idioma do tooltip variam por browser/SO — no Firefox ou Safari o texto muda, alguns leitores de tela o ignoram completamente, e ele não respeita o container do modal (pode aparecer cortado em viewports pequenos).
**Recomendação:** remover `required` nativo do campo (ou usar `novalidate` no form) e depender exclusivamente da validação server-side já implementada, que retorna corretamente o fragment do modal com erro inline.

Evidência: `screenshots/modal-recusa-erro-vazio.png`.

#### A2 — Documentação de arquitetura de informação desatualizada em relação ao código
**O quê:** `.design/INFORMATION_ARCHITECTURE.md` não lista a rota `/requisicoes/historico/` (nem o link "Histórico de requisições" no drawer) e restringe "Nova requisição" a Solicitante/Auxiliar de setor — mas o chefe de setor (OBRAS001) também vê esse link no drawer atual.
**Impacto:** não é um bug de experiência para o usuário final, mas é um risco real: decisões futuras de design/revisão (inclusive esta auditoria, inicialmente) partem de uma IA que não reflete o sistema em produção. Aumenta a chance de inconsistência se um novo brief for escrito a partir do documento desatualizado.
**Recomendação:** atualizar a IA como parte do fechamento da feature de Histórico (ou vincular a atualização da IA como critério de definição de pronto para novas rotas).

---

### Médios

#### M1 — Drawer único mesmo em desktop custa cliques extras sem ganho aparente
**O quê:** por decisão documentada (Q5/B2 em `topbar/DESIGN_BRIEF.md`), a navegação principal fica sempre atrás do hamburger, inclusive em 1280px, onde sobra espaço horizontal de sobra na topbar.
**Impacto:** decisão intencional e documentada, mas o custo de usabilidade é real: em telas de uso repetitivo (chefe checando fila de autorização várias vezes ao dia), cada troca de contexto exige abrir o drawer, localizar o link, fechar. Um padrão de nav inline em `lg+` é comum nesse tipo de ferramenta interna justamente para reduzir esse atrito.
**Recomendação:** revisitar a decisão Q5/B2 com dados de uso real (se disponíveis) — considerar nav inline em `lg+` mantendo o drawer em mobile/tablet.

#### M2 — Campo "Atualizada em" redundante no cabeçalho do detalhe
**O quê:** o cabeçalho de detalhe mostra tanto "Atualizada em" quanto "Enviada em" com o **mesmo timestamp** em requisições recém-enviadas (e em outros estados, "Atualizada em" frequentemente duplica outro campo já visível). Esse campo não consta na lista de campos do brief (`detalhe-requisicao/DESIGN_BRIEF.md`, seção 1).
**Impacto:** ruído informacional — dois rótulos, um dado, sem explicar a diferença ao usuário.
**Recomendação:** remover "Atualizada em" do cabeçalho ou substituí-lo por um campo que agregue valor real (ex: label do último evento de timeline).

#### M3 — Coluna "Material" no Histórico mistura tipos de dado
**O quê:** na tela de Histórico, a coluna "Material" mostra o nome do material para requisições de item único ("Papel A4") e `"N itens"` para requisições multi-item — dois tipos de conteúdo semanticamente diferentes na mesma coluna, sem indicação visual da diferença.
**Impacto:** dificulta escaneabilidade — usuário não consegue prever, olhando a coluna, se está vendo "o material" ou "quantos materiais".
**Recomendação:** padronizar para sempre mostrar contagem ("1 item" / "N itens") com o material como informação secundária, ou permitir hover/expansão para listar todos os materiais.

#### M4 — Badges "Recusada" e "Cancelada" compartilham a mesma cor
**O quê:** ambos os estados usam `bg-red-200`/`text-red-900` (`_estado_badge.html`). São dois estados terminais com semânticas de negócio diferentes (recusa = nunca autorizada; cancelamento = encerrada em qualquer ponto do fluxo), mas visualmente idênticos.
**Impacto:** na tela de Histórico — onde múltiplas linhas de estados diferentes aparecem lado a lado — o usuário precisa ler o texto para diferenciá-los; a cor não ajuda na triagem visual rápida, indo contra o próprio princípio de "badge de estado" do design system.
**Recomendação:** diferenciar tonalidade (ex.: manter vermelho para Recusada, usar âmbar/laranja para Cancelada) mantendo ambos claramente na família "estado negativo".

#### M5 — Overflow horizontal sem indicador visual no formulário de atendimento (mobile)
**O quê:** a tabela de itens em `/requisicoes/<id>/atender/` usa `overflow-x-auto` (mobile 375px) mas, diferente da tabela de detalhe, não tem sombra/gradiente indicando que há mais colunas à direita — a coluna "Justificativa" fica completamente fora da viewport inicial, sem pista visual de que existe.
**Impacto:** o brief (`detalhe-requisicao/DESIGN_BRIEF.md`, P1-06) exige explicitamente esse indicador; sem ele, o almoxarife em campo (celular) pode não perceber que precisa rolar para preencher a justificativa de uma entrega parcial — campo que é **obrigatório** nesse cenário.
**Recomendação:** aplicar o mesmo padrão de sombra/gradiente lateral já usado (ou a ser padronizado) na tabela de itens do detalhe.

#### M6 — Hierarquia visual: ação destrutiva aparece antes da ação primária
**O quê:** no detalhe de uma requisição "Pronta para retirada", o card vermelho "Cancelar requisição" aparece **acima** do card azul "Registrar retirada" na ordem de leitura vertical — apesar de "Registrar retirada" ser a ação esperada no caminho feliz.
**Impacto:** o card vermelho, com borda e fundo coloridos, chama mais atenção visual e aparece primeiro — na prática compete com a ação primária pelo olhar do usuário, na direção oposta ao princípio "ação primária = mais peso visual" do próprio brief.
**Recomendação:** inverter a ordem (ação de avanço de fluxo primeiro, cancelamento por último) ou reduzir o peso visual do card de cancelamento quando não for a ação mais provável.

---

### Baixos

#### B1 — Cópia duplicada entre card de gatilho e modal
**O quê:** em vários blocos de ação (ex.: "Retornar para rascunho"), o texto descritivo do card que abre o modal repete quase literalmente o texto dentro do modal.
**Impacto:** redundância de leitura, não bloqueia a tarefa.
**Recomendação:** diferenciar a copy — o card pode ser mais curto/orientado à ação, o modal foca na confirmação/consequência.

#### B2 — Notificação de exemplo sem vínculo de requisição quebra o alinhamento da lista
**O quê:** a última notificação da lista de exemplo (seed) não tem a linha "Requisição #N", deixando a altura/alinhamento do item diferente dos demais.
**Impacto:** cosmético, restrito a dado de seed; mas indica que o template não tem tratamento visual definido para notificações sem `requisicao_id` (podem ocorrer em produção também).
**Recomendação:** definir um estado visual consistente para notificação sem requisição vinculada.

---

## O que funciona bem

- **Fluxo de estado → ação é claro e correto** em todos os papéis testados: as ações disponíveis por papel/estado batem exatamente com a matriz do brief (`detalhe-requisicao/DESIGN_BRIEF.md`), sem botões desabilitados ou ações fantasmas.
- **Modais de confirmação** (exceto A1) seguem consistentemente o padrão Material — foco movido ao abrir, `role="dialog"`, `aria-modal`, botão "Voltar" fecha sem submeter, PRG com `messages.success` após ação.
- **Mensagens de feedback** (`_messages.html`) usam `role="status"`/`aria-live`, texto específico com número da requisição, e aparecem no contexto certo após redirect.
- **Responsividade das tabelas**: tanto a lista de Minhas Requisições quanto o Histórico colapsam corretamente para cards empilhados em mobile, mantendo as informações essenciais visíveis sem exigir scroll horizontal nesses casos específicos.
- **Semântica HTML**: uso consistente de `<thead>`, `<th scope="col">`, `<caption class="sr-only">`, `<dl>` para pares label/valor no cabeçalho — base de acessibilidade sólida.
- **Botão "Registrar retirada"** já corrigido para estilo primário sólido (P2-10 do QA anterior confirmado como resolvido em código, apesar do checklist em `TASKS_REMEDIATION.md` ainda estar desmarcado).
- **RBAC no nível de queryset** (não em view/template) para "Minhas Requisições" — rascunho de terceiro corretamente oculto do beneficiário, só falhando (C1) no módulo de Histórico.

---

## Resumo executivo — Top 5 recomendações por impacto

1. **Corrigir o vazamento de RBAC no Histórico (C1)** — excluir `RASCUNHO` do queryset `historico_requisicoes_visiveis_para`. Maior risco: expõe trabalho privado de terceiros e quebra com 404.
2. **Corrigir o pré-preenchimento do formulário de atendimento (C2)** — `localize=False` no campo de quantidade entregue. Afeta a operação mais repetida do sistema, hoje forçando redigitação manual em toda entrega.
3. **Tornar notificações acionáveis e remover vazamento de PK (C3)** — trocar `#PK` por número público e linkar cada item à requisição. Alta visibilidade (ícone em toda tela), baixo esforço de implementação, alto ganho de utilidade.
4. **Substituir validação nativa do browser no modal de recusa (A1)** por erro inline consistente com o design system — pequeno ajuste, mas acontece exatamente no ponto de maior atenção do usuário (correção de erro em ação irreversível).
5. **Sincronizar `.design/INFORMATION_ARCHITECTURE.md` com o código atual (A2)** e formalizar um brief mínimo para Histórico/Notificações — hoje são as duas telas mais usadas sem cobertura de design documentada, o que provavelmente explica por que concentram a maioria dos achados críticos desta auditoria.

---

## Screenshots capturados

Todos em `.design/audit-uiux-2026-07/screenshots/`:

| Arquivo | Contexto |
|---|---|
| `login-desktop-1280.png` / `login-mobile-375.png` | Tela de login |
| `minhas-requisicoes-com-dados-desktop-1280.png` | Lista "Minhas Requisições" |
| `drawer-mobile-desktop-1280.png` | Drawer de navegação aberto (desktop) |
| `detalhe-aguardando-autorizacao-desktop.png` | Detalhe, estado aguardando autorização |
| `modal-retornar-rascunho-desktop.png` | Modal "Retornar para rascunho?" |
| `fila-autorizacao-desktop-1280.png` | Fila de autorização (chefe de setor) |
| `detalhe-chefe-acoes-desktop.png` | Ações de autorizar/recusar |
| `modal-recusa-erro-vazio.png` | Tooltip nativo de validação (A1) |
| `fila-autorizacao-apos-recusa-msg.png` | Mensagem de sucesso pós-recusa |
| `historico-desktop-1280.png` / `historico-mobile-375.png` | Histórico de requisições (C1) |
| `fila-atendimentos-desktop-1280.png` | Fila de atendimento (almoxarifado) |
| `detalhe-pronta-retirada-desktop.png` | Detalhe + CTA "Registrar retirada" |
| `atender-formulario-desktop.png` / `atender-formulario-mobile-375.png` | Formulário de atendimento (C2, M5) |
| `detalhe-rascunho-desktop.png` | Ações de rascunho (editar/enviar/descartar) |
| `notificacoes-desktop.png` | Central de notificações (C3) |
