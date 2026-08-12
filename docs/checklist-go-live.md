# Checklist de go-live

Conferências a fazer no ambiente de produção **antes** de liberar o sistema aos
usuários, e a cada retomada após manutenção que toque dados de estoque.

Cada item registra o que conferir, como conferir e o que fazer quando a
conferência falha.

## Estoque

### GL-01 — Existe exatamente um `Estoque`

**Por quê?** Os services de estoque assumem um único `Estoque` nesta fase
(ADR-0017): localizam saldo apenas por `material_id`, sem `estoque_id`, e
tratam "mais de um `SaldoEstoque` para o mesmo material" como erro. Um segundo
estoque com saldo para um material já usado quebra **globalmente** autorização,
separação, atendimento e cancelamento de qualquer setor, com uma mensagem
(`saldo_ambiguo` / `separacao_bloqueada`) que não indica a causa.

`EstoqueAdmin.has_add_permission` barra a criação de um segundo estoque pela
interface do admin, mas **não** cobre criação por shell, `seed_dev` ou
migration — daí este item de checklist.

**Como conferir?**

```sql
SELECT id, codigo, nome, ativo FROM estoque_estoque;
```

Esperado: exatamente uma linha, com `ativo = true`.

**Detecção do sintoma** — materiais com saldo em mais de um estoque:

```sql
SELECT material_id, count(*)
FROM estoque_saldoestoque
GROUP BY material_id
HAVING count(*) > 1;
```

Esperado: nenhuma linha. Qualquer linha retornada é um material cuja
autorização, separação e atendimento já estão quebrados.

**Se falhar.** Não libere o sistema. Consolide os saldos em um único `Estoque`
antes de seguir — apagar um `Estoque` com `SaldoEstoque` e
`MovimentacaoEstoque` associados é operação destrutiva e não há service que a
suporte; a consolidação precisa de runbook próprio, com backup e migração de
saldos e do ledger.

Se o segundo estoque foi criado por engano e ainda **não** tem saldos nem
movimentações, apagá-lo resolve o item.

## Autenticação

### GL-02 — Lockout de login ativo e ancorado no IP certo

**Por quê?** O login por matrícula é a única porta do sistema, e o namespace de
matrículas é adivinhável. O lockout do `django-axes` (ADR-0018) é o que impede
força bruta, mas ele depende de duas coisas que só se confirmam no ambiente
real: as tabelas do pacote existirem, e o IP resolvido corresponder ao cliente
de verdade.

Os dois modos de falha são silenciosos de formas opostas. Migration não
aplicada quebra o login inteiro no primeiro acesso. Resolução de IP errada não
quebra nada — só faz o bloqueio proteger a coisa errada.

**Como conferir?**

1. **Migrations aplicadas.** As quatro tabelas do axes precisam existir:

   ```sql
   SELECT tablename FROM pg_tables
   WHERE tablename LIKE 'axes_%'
   ORDER BY tablename;
   ```

   Esperado: `axes_accessattempt`, `axes_accessattemptexpiration`,
   `axes_accessfailurelog`, `axes_accesslog`. Faltando qualquer uma, rode
   `manage.py migrate`.

2. **Resolução de IP bate com a topologia.** Faça uma tentativa de login com
   senha errada, de uma máquina cliente comum, e confira o IP registrado:

   ```sql
   SELECT username, ip_address, attempt_time
   FROM axes_accessattempt
   ORDER BY attempt_time DESC
   LIMIT 5;
   ```

   Esperado: o IP da máquina do cliente. Dois resultados errados possíveis:

   - **IP do proxy em todas as linhas** — `PILOTO_ATRAS_DE_PROXY_TLS` está
     desligado, mas há proxy na frente. Todos os usuários compartilham um balde
     de bloqueio: quem souber uma matrícula tranca aquela pessoa. Ligue a
     variável.
   - **`ip_address` nulo** — a requisição chegou ao Django **sem** passar pelo
     proxy, e `AXES_IPWARE_PROXY_COUNT` a descartou. Isso significa que o Django
     está exposto diretamente. Feche o acesso: ele deve escutar só em localhost
     ou atrás de firewall, alcançável apenas pelo proxy.

3. **O bloqueio dispara.** Com uma matrícula descartável, erre a senha cinco
   vezes. Esperado: a quinta responde a página de acesso bloqueado (HTTP 429).
   Depois, desbloqueie a matrícula de teste (comandos abaixo).

**Se falhar.** Não libere o sistema até os três itens passarem. O item 1 é
correção direta (`migrate`); o item 2 é configuração de implantação; o item 3
falhando com 1 e 2 corretos indica configuração de `AXES_*` divergente do
ADR-0018.

### Operação do lockout

Comandos que a equipe de suporte vai precisar:

```bash
python manage.py axes_list_attempts
```

```bash
python manage.py axes_reset_username <matricula>
```

```bash
python manage.py axes_reset_ip_username <ip> <matricula>
```

O expurgo dos registros de auditoria usa **comandos distintos** — um não cobre o
outro:

```bash
python manage.py axes_reset_logs --age <dias>
```

```bash
python manage.py axes_reset_failure_logs --age <dias>
```

`axes_reset_logs` apaga `AccessLog` (acessos bem-sucedidos);
`axes_reset_failure_logs` apaga `AccessFailureLog` (falhas). Ambos guardam
matrícula, IP e user-agent, e não há rotina agendada de expurgo nesta fase.
