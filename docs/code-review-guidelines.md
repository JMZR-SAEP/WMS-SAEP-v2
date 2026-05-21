# Diretrizes de code review

Este documento define invariantes arquiteturais e regras críticas de domínio que devem orientar revisões de Pull Request neste projeto.

Objetivo: fazer revisões alinhadas ao WMS-SAEP-v2 real, evitando sugestões genéricas ou herdadas de projetos anteriores.

## Fontes de verdade

Antes de sugerir mudança que altere regra de domínio, fluxo de usuário ou arquitetura, confira:

- `CONTEXT.md`: linguagem ubíqua do domínio.
- `docs/CONVENTIONS.md`: regras operacionais para implementação.
- `docs/adr/`: decisões arquiteturais aceitas.
- `docs/matriz-permissoes.md`: autorização por papel efetivo e setor.
- `docs/matriz-invariantes.md`: invariantes de domínio.
- `docs/estado-transicoes-requisicao.md`: estados e transições de requisição.
- `docs/design-system.md`: Django templates, Tailwind, HTMX e Alpine.js.

Se docs e código divergem, sinalize o conflito. Não normalize a divergência em silêncio.

## Ambiente efêmero

O ambiente local de desenvolvimento é descartável. O fluxo padrão é recriar banco e materializar migrations locais do zero quando há mudança estrutural.

- `rtk make init`: setup inicial de `.venv` e dependências.
- `rtk make setup`: recria/materializa ambiente local quando há edição de `models` ou schema.
- `rtk make seed-dev`: converge dados canônicos locais quando o comando existir no fluxo.

Implicações para review:

- Migrations locais de apps são artefatos efêmeros.
- Não exigir commit de migrations geradas para o ambiente local.
- Não pedir edição manual de migration local como correção normal.
- Em mudança de schema, priorizar models, constraints, índices, invariantes e testes.

Exceção: se o PR declara preparação para staging/produção ou migração real de dados, revise risco destrutivo, compatibilidade e plano de aplicação.

## Arquitetura em camadas

Apps de domínio seguem o contrato de `docs/CONVENTIONS.md` e ADR-0004.

- `models.py`: schema, constraints, choices e properties simples.
- `services.py`: único ponto de mutação de domínio.
- `policies.py`: autorização contextual compartilhada.
- `selectors.py`: leituras não triviais, filas e escopos de visibilidade.
- `forms.py`: validação de input HTTP.
- `views.py`: camada fina de request/response.
- `transitions.py`: fonte declarativa da máquina de estados de requisição, quando aplicável.

Não aceitar:

- regra de negócio central em `views.py`;
- transição de estado em `forms.py`, `admin.py`, managers ou signals;
- mutação operacional de saldo fora de service;
- policy duplicada em view e service;
- model chamando service ou orquestrando caso de uso em `save()`;
- helper genérico escondendo regra de domínio crítica.

## Services

Services públicos devem:

- usar assinatura keyword-only;
- receber IDs, não instâncias ORM, para entidades operacionais;
- carregar ator e entidades internamente;
- abrir `transaction.atomic()` quando há escrita de domínio;
- chamar `exigir_pode_*` da policy;
- validar transição via fonte declarativa quando aplicável;
- registrar timeline ou model de auditoria de domínio na mesma transação;
- disparar notificações apenas via `transaction.on_commit`;
- lançar exceções de `apps.core.exceptions`, nunca exceções HTTP do Django.

Qualquer escrita de domínio fora desse contrato é alto risco.

## Policies e selectors

Policies são a fonte de verdade da autorização contextual.

- Cada operação deve ter `pode_*` e `exigir_pode_*`.
- `exigir_pode_*` sempre delega para `pode_*`.
- Services chamam `exigir_pode_*`.
- Views/templates podem usar `pode_*` para renderização e UX.

Selectors concentram escopo de leitura e visibilidade:

- filas de autorização e atendimento;
- listagens por papel efetivo;
- visibilidade por setor;
- consultas não triviais.

Review deve procurar IDOR, vazamento entre setores, superusuário como operador cotidiano e regra de visibilidade escondida em filtros ou templates.

## Requisições

Revisar contra `docs/estado-transicoes-requisicao.md`, matriz de permissões, matriz de invariantes e ADRs 0003, 0005, 0006 e 0007.

Pontos críticos:

- rascunho, envio, autorização, recusa, cancelamento e atendimento;
- `Criador`, `Beneficiário` e `Retirante` não são sinônimos;
- requisição pertence ao Setor do Beneficiário;
- autorização cabe ao Chefe de setor do Setor do Beneficiário;
- número público anual nasce apenas no primeiro envio e é imutável;
- snapshots de setor/beneficiário usados para rastreabilidade não devem depender de cadastro mutável atual;
- timeline deve registrar eventos de domínio relevantes;
- transições concorrentes devem recarregar `Requisicao` sob `select_for_update()`.

Não aceitar transições espalhadas em `if/elif` fora do service/fonte declarativa.

## Estoque

Pontos críticos:

- `saldo_disponivel = saldo_fisico - saldo_reservado`;
- não permitir saldo negativo indevido;
- não permitir reserva acima do disponível;
- não permitir material inativo em nova requisição;
- mutação operacional de saldo/reserva deve ser transacional;
- quando houver concorrência, usar locking e ordem determinística.

O seed pode escrever saldo inicial diretamente apenas como exceção de bootstrap documentada. Fluxos reais da aplicação devem usar services.

## Auditoria e rastreabilidade

Auditoria operacional é feita por models de domínio explícitos, conforme ADR-0002.

- `TimelineRequisicao` registra eventos curados do ciclo de vida da requisição.
- Mutações de estoque devem ser representadas por conceitos/models de domínio, como movimentação e reserva, quando implementadas.
- Não usar `django-simple-history` nesta fase.
- Não substituir timeline por signals genéricos de `save()`.
- Não usar snapshots técnicos automáticos como histórico visível ao usuário.

Correções de fatos auditáveis devem preservar o histórico original e criar evento/registro compensatório quando o domínio exigir.

## Notificações e side effects

Notificações não são domínio e não são pré-condição de transição.

Não aceitar:

- notificação contendo regra de negócio;
- notificação decidindo se transição pode acontecer;
- falha de notificação desfazendo operação já válida;
- import direto que faça app de side effect controlar fluxo crítico de domínio.

Side effects de escrita devem ser acionados depois do commit com `transaction.on_commit`.

## Frontend server-rendered

A direção aceita é Django templates + Tailwind + HTMX + Alpine.js. Não sugerir SPA, React/Vue ou biblioteca JS própria sem nova decisão arquitetural.

Review deve verificar:

- componentes globais em `apps/core/templates/components/` sem semântica de negócio;
- partials de domínio dentro do app dono;
- URLs em PT-BR;
- mensagens em PT-BR, orientadas ao usuário e sem termos técnicos internos;
- acessibilidade, contraste, foco e ARIA;
- POST bem-sucedido com HTMX usando redirect apropriado, não swap parcial de escrita;
- ausência de texto de ajuda técnico dentro da UI.

## Seed dev

`seed_dev` é fonte de verdade para dados canônicos locais.

Review deve garantir:

- proteção por `DEBUG=True` e `SEED_DEV_HABILITADO=true`;
- escrita declarativa, convergente e idempotente;
- `update_or_create` para entidades canônicas;
- `SequenciaRequisicao` com `get_or_create`, sem reset de contador;
- nenhuma criação de `Requisicao`, `TimelineRequisicao` ou movimentação artificial;
- superusuário canônico usado apenas como suporte/admin técnico.

## Testes

Aplicar ADR-0010:

- models: constraints não triviais e properties semânticas;
- policies: matriz de autorização direta;
- selectors: visibilidade e escopo por conjuntos de IDs;
- services: caminho feliz, estado inválido, permissão negada, efeitos e timeline;
- views: contrato HTTP, autenticação, autorização, redirect/renderização.

Não duplicar:

- matriz completa de policy em teste de service;
- matriz completa de selector em teste de view;
- efeitos internos de service em teste de view.

Não usar `factory_boy` nesta fase. Não usar `seed_dev` como pré-condição de teste.

## Anti-padrões de review

Evitar:

- sugerir "boa prática" genérica sem problema real;
- sugerir migrations versionadas no fluxo efêmero normal;
- sugerir camada de API como padrão quando a fatia é server-rendered;
- sugerir SPA ou tooling frontend pesado sem decisão nova;
- pedir abstração antes de haver duplicação ou complexidade concreta;
- ignorar vocabulário do `CONTEXT.md`;
- usar superusuário como atalho para validar fluxo operacional;
- tratar SQLite como prova de locking quando o comportamento depende de concorrência real.

## Checklist final

Antes de sugerir mudança, pergunte:

1. A sugestão respeita as invariantes do domínio?
2. A sugestão respeita ambiente efêmero e migrações locais?
3. A sugestão mantém regra de domínio no service/policy/selector correto?
4. A sugestão preserva auditoria e rastreabilidade por models de domínio?
5. A sugestão melhora risco real ou é só preferência genérica?

Se for preferência genérica, não comentar. Se quebrar invariante, tratar como alto risco.
