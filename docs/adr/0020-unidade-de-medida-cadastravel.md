# ADR-0020 — Unidade de medida cadastrável

## Status

Aceita

## Contexto

`Material.unidade` era um `CharField` com `choices` de um `TextChoices` fixo de
nove valores (`un`, `cx`, `pct`, `par`, `rolo`, `m`, `m2`, `kg`, `l`). A
precisão com que cada quantidade é exibida, e o `step` do campo que a digita,
saíam de uma tabela de códigos em `apps/core/quantidades.py`: `un` inteiro,
`kg`/`l`/`m` com uma casa, o resto por casa significativa.

A importação SCPI criava todo material novo com `un`, porque se supunha que o
CSV não informava unidade (#219). O export real anexado na #171 desmente isso: a
coluna `UNID1` existe, com 22 códigos distintos em 628 materiais. Parte deles
não tem equivalente no enum — `BR` (barra, 22 materiais), `T` (tonelada, 7),
`KIT`, `SC`, `GL`, `ML`, `FL`, `MC`, `RM` — e dois deles (`BR`, `MC`) já trazem
quantidade fracionada no próprio arquivo. `T` e `ML` também não podem virar
`kg` e `l`: converter mudaria a quantidade e quebraria a comparação de saldo
com o SCPI nas importações seguintes.

Um enum fixo obriga deploy para cada unidade nova que o SCPI passar a usar, e a
precisão em código obriga deploy para cada ajuste de exibição.

## Decisão

1. `UnidadeMedida` é um model com `codigo` como chave primária, `nome` e
   `casas_decimais` (0 a 3, por `CheckConstraint`: saldo e quantidade são
   `DecimalField(decimal_places=3)`). `Material.unidade` é FK com `PROTECT`.
2. **O código é a chave primária** para que `material.unidade_id` continue sendo
   o texto curto que o template imprime, o JS lê em `data-unidade` e o CSV
   exporta, sem consulta extra. `__str__` devolve o código. O código é somente
   leitura no admin depois de criado.
3. **A precisão é dado da unidade.** `apps/core/quantidades.py` recebe um objeto
   com `casas_decimais` (protocolo `Unidade`) e segue sem importar Django. O
   código em texto é recusado com `TypeError`, e não degradado, porque sozinho
   ele não diz mais a precisão. `None` ou vazio degradam para 3 casas
   significativas, como antes.
4. **Não há carga obrigatória de unidades.** `UNIDADES_CONHECIDAS`
   (`apps/estoque/models.py`) guarda nome e precisão das unidades que o sistema
   sabe medir. Ela alimenta:
   - o `seed_dev`, que as cria por `update_or_create` (ADR-0009);
   - os testes, pelo helper `apps/estoque/tests/unidades.py::obter_unidade`;
   - a importação SCPI, que cria a unidade que falta no ato da confirmação, sem
     sobrescrever uma já cadastrada.

   No banco do piloto, unidade usada fora da importação é cadastrada no admin.
   Descartados: handler de `post_migrate` (dado de referência escondido num
   sinal) e comando de carga obrigatório no deploy (passo esquecível).
5. `LinhaDivergenteSCPI.unidade` é FK nulável com `PROTECT`, não texto copiado.
   O código não muda e `PROTECT` impede apagar unidade citada, então o
   instantâneo continua legível. O que acompanha o catálogo é só a precisão de
   exibição, que é política de leitura; o saldo gravado não muda.
6. Gestão no admin segue o `MaterialAdmin`: superusuário apenas.

## Consequências

- Todo queryset que renderiza quantidade precisa de
  `select_related('material__unidade')` (ou `'unidade'`), senão cada linha faz
  uma consulta para achar as casas decimais.
- `get_unidade_display` deixa de existir; a forma por extenso é
  `material.unidade.nome`.
- Teste que cria `Material` precisa criar a unidade antes (`obter_unidade`).
- A importação lê a coluna `UNID1` só para material novo; o existente fica com
  a unidade do WMS, sem alerta de divergência de unidade. O valor normalizado
  (sem espaços nas pontas, maiúsculas) passa por `SINONIMOS_UNIDADE_SCPI`
  (`apps/estoque/models.py`) e, fora dele, vira o próprio valor em minúsculas;
  coluna ausente ou valor vazio cai em `un`. O preview resolve a unidade de
  cada código numa consulta só — a cadastrada, senão a de
  `UNIDADES_CONHECIDAS`, senão uma nova com o valor do CSV como nome e 3 casas
  — e anuncia a que falta como instância não salva. A confirmação cria
  exatamente essas num `bulk_create(ignore_conflicts=True)`: unidade já
  cadastrada, inclusive por outra confirmação concorrente, não é sobrescrita.
  Não há conversão de quantidade. Código normalizado acima de 10 caracteres é
  recusado no preview (`csv_unidade_muito_longa`), antes de qualquer escrita
  (#219).

## Trade-off

Aceita-se um `JOIN` a mais nas listagens e uma FK em todo material em troca de
unidade nova e ajuste de precisão sem deploy. A alternativa — ampliar o enum a
cada código novo do SCPI — é mais barata hoje, mas depois do D0 do piloto
transformaria cada unidade nova em deploy e cada migração de schema em
migração de dados real.
