# Plano — Issue #69: mensagens duplicadas no detalhe da saída excepcional

## Escopo

`apps/estoque/templates/estoque/detalhe_saida_excepcional.html` reimplementa
inline o bloco `{% if messages %}` (linhas 12-27) com estilo próprio
(ring/cores divergentes). O template estende `estoque/base.html` →
`base_auth.html`, que já inclui `core/partials/_messages.html` antes de
`{% block content %}` (`apps/core/templates/base_auth.html:196`). Resultado:
após um POST com `django.contrib.messages` (ex.: estorno de saída
excepcional), a mesma mensagem aparece duas vezes, com dois estilos.

**Muda:** remove o bloco inline de messages (linhas 12-27) de
`detalhe_saida_excepcional.html`.

**Não muda:** `core/partials/_messages.html` (estilo, ARIA, `aria-live`),
`base_auth.html`, qualquer outro template, comportamento de domínio
(services/policies/selectors).

Confirmado por `grep -rn "{% if messages %}" apps/ --include="*.html"`: única
ocorrência fora de `_messages.html` é a de `detalhe_saida_excepcional.html`.
Nenhuma outra reimplementação existe no projeto.

## Arquivos tocados

- `apps/estoque/templates/estoque/detalhe_saida_excepcional.html` — remove
  linhas 12-27 (bloco `{# Mensagens de sistema #}` + `{% if messages %}...{% endif %}`).

Nenhum outro arquivo precisa mudar. Sem mudança de classes Tailwind novas —
apenas remoção de classes existentes no bloco deletado, então `npm run
css:build` não é estritamente necessário (nenhuma classe passa a ficar órfã
em outro lugar, pois eram exclusivas desse bloco). Será rodado por precaução
e `app.css` incluído no diff apenas se houver diferença real.

## Test strategy

Este é um fix de template puro (deduplicação de renderização), sem lógica de
view/service/policy nova. Cobertura:

- **Teste view/template existente**: localizar teste que exercita
  `detalhe_saida_excepcional` após uma ação que gera `messages.success`
  (ex.: registrar estorno) e afirmar que a mensagem aparece **uma única vez**
  no HTML renderizado (contagem de ocorrências da string da mensagem, ou
  contagem de blocos com `role="status"`/`role="alert"`).
- Caso não exista teste desse fluxo hoje, adicionar um teste de view mínimo
  que faz o POST de estorno e verifica contagem == 1 no response content.
- Não há caminho de erro/policy novo — o fix não introduz branch de decisão.

## Invariantes (docs/design-acesso-rapido/matriz-invariantes.md)

Não há mudança de regra de negócio, RBAC ou state machine. Invariante
relevante é de UI/contrato de mensagens (`project_messages_contract`
memória): níveis error/warning usam `role="alert"`, success/info usam
`role="status"`, ambos com `aria-live` — comportamento já garantido por
`_messages.html` e preservado por não ser tocado.

## Riscos

- Baixo. Mudança é subtração de HTML duplicado, sem lógica nova.
- Único risco real: algum teste existente afirmar hoje sobre o bloco inline
  removido (ex.: buscando classes `ring-green-200` etc.) — nesse caso o
  teste precisa ser ajustado para refletir o partial global.
