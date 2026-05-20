# ADR-0001 — Papéis de domínio derivados, sem campo de papel no Usuário

## Status

Aceita

## Contexto

A documentação lista seis "papéis" heterogêneos: solicitante, auxiliar de setor, chefe de setor, auxiliar de almoxarifado, chefe de almoxarifado e superusuário.

Esses conceitos não têm a mesma natureza:

- Solicitante é uma capacidade implícita de todo usuário ativo.
- Auxiliar de setor é um vínculo atribuído entre Usuário e Setor.
- Chefe de setor é derivado da chefia do Setor.
- Auxiliar de almoxarifado é derivado de vínculo com o Setor classificado como almoxarifado.
- Chefe de almoxarifado é derivado da chefia do Setor classificado como almoxarifado.
- Superusuário é uma flag técnica do Django.

Um campo global como `User.role` duplicaria fatos já representados por chefia, vínculos e flags técnicas, permitindo divergência entre dados.

## Decisão

Não armazenar papel de domínio como campo, enum ou relação global no Usuário.

Todo usuário ativo é implicitamente solicitante.

Auxiliar de setor será modelado como vínculo explícito Usuário↔Setor, ativável/desativável.

Chefe de setor será derivado da relação de chefia do Setor. Um Setor tem um chefe, e um chefe responde por no máximo um Setor.

Almoxarifado será representado como um Setor classificado como almoxarifado. Chefe de almoxarifado e auxiliar de almoxarifado serão derivados dessa classificação combinada com chefia/vínculo.

Superusuário continuará sendo apenas `User.is_superuser` do Django e não será tratado como papel de domínio.

O papel efetivo será calculado por policies a partir de ator + contexto.

## Consequências

Não criar `User.role`.

Não criar `User.is_solicitante`.

Não criar `User.is_chefe_setor`.

Não criar `User.is_auxiliar_almoxarifado`.

Não criar enum global de papéis de domínio no Usuário.

Helpers organizacionais básicos podem existir em `accounts`, por exemplo:

- `is_chefe_do_setor(user, setor)`
- `is_auxiliar_do_setor(user, setor)`
- `is_chefe_almoxarifado(user)`
- `is_auxiliar_almoxarifado(user)`

Policies de caso de uso devem morar no app dono do caso de uso:

- `requisicoes.policies` para permissões sobre requisições.
- `estoque.policies` para permissões sobre estoque, importação, divergência e saída excepcional.

## Trade-off

As policies precisarão consultar estrutura organizacional e vínculos para calcular o papel efetivo. Aceitamos esse custo em troca de consistência estrutural e eliminação de estados divergentes, como um usuário marcado como chefe sem chefiar nenhum setor.
