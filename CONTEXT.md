# WMS-SAEP

Contexto único de gestão do almoxarifado da SAEP: cobre requisições de
material, autorização, atendimento e controle de estoque. Este arquivo é o
glossário de domínio — sem detalhes de implementação.

## Language

### Organização e papéis

**Usuário**:
Pessoa com acesso ao sistema; pertence a exatamente um Setor.
_Avoid_: funcionário, colaborador

**Setor**:
Unidade organizacional da SAEP à qual um Usuário pertence.

**Almoxarifado**:
O Setor responsável pela guarda e entrega de materiais; é um Setor com
classificação própria, não uma entidade à parte.

**Chefe de setor**:
Usuário responsável por um Setor; autoriza ou recusa as requisições desse
Setor. Papel derivado de ser o chefe daquele Setor, não um atributo fixo do
Usuário.
_Avoid_: gerente, responsável

**Auxiliar de setor**:
Usuário com vínculo de apoio a um Setor, habilitado a criar requisições em
nome de outros Usuários do mesmo Setor.

**Chefe de Almoxarifado**:
O Chefe do Setor Almoxarifado; único papel autorizado a estornar e a
registrar saída excepcional.

**Auxiliar de Almoxarifado**:
Usuário com vínculo de apoio ao Setor Almoxarifado; executa separação,
atendimento e devolução.

**Solicitante**:
Condição implícita de todo Usuário ativo, capaz de criar requisições para si
mesmo; não é um papel atribuído.
_Avoid_: requerente

**Papel efetivo**:
O papel que um ator exerce diante de um Setor ou requisição específicos,
calculado a partir do ator e do contexto — nunca um atributo fixo do Usuário.

### Atores da requisição

**Criador**:
Usuário que registrou a requisição.

**Beneficiário**:
Usuário que receberá o material; define o Setor da requisição e a fila de
autorização.
_Avoid_: destinatário, solicitante

**Retirante**:
Pessoa que coleta fisicamente o material no momento do atendimento; pode não
ser o Beneficiário.

## Relationships

- Cada **Usuário** pertence a exatamente um **Setor**.
- Cada **Setor** tem exatamente um **Chefe de setor**.
- Um **Chefe de setor** responde por no máximo um **Setor**.
- O **Almoxarifado** é um **Setor**.
- Um **Auxiliar de setor** tem vínculo ativo com um **Setor**; o vínculo pode
  ser desativado.
- Uma requisição pertence ao **Setor** do **Beneficiário**, nunca ao do
  **Criador**.
- O **Chefe de setor** autorizador de uma requisição é o chefe do **Setor do
  Beneficiário**.

## Example dialogue

> **Dev:** "O Usuário tem um campo que diz se ele é chefe de setor?"
> **Especialista:** "Não. Ele é chefe porque é o chefe de um Setor. Se você
> tirar ele da chefia daquele Setor, ele deixa de ser chefe — não tem o que
> atualizar no cadastro dele."
> **Dev:** "E se o Almoxarifado cria uma requisição para alguém de Obras,
> quem autoriza?"
> **Especialista:** "O chefe de Obras. A requisição é do Setor de quem
> recebe, não de quem digitou."

## Flagged ambiguities

- "Papel" era usado para conceitos heterogêneos (default implícito, vínculo
  de setor, chefia derivada, flag técnica). Resolvido: papel não é campo único
  no Usuário — **Solicitante** é implícito, **Auxiliar de setor** é vínculo
  explícito, **Chefe de setor** é derivado da chefia do Setor; superusuário é
  apenas a flag técnica do Django, fora do domínio.
- "Solicitante", "Criador" e "Beneficiário" eram usados de forma
  intercambiável. Resolvido: são distintos — Solicitante é a capacidade
  implícita, Criador é quem registrou, Beneficiário é quem recebe.
- "Almoxarifado" designava tanto um Setor quanto um escopo operacional.
  Resolvido: é um Setor classificado como almoxarifado; os papéis de
  almoxarifado derivam dele.
