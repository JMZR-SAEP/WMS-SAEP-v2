# Plano — Issue #115: arquivar o CSV da importação SCPI como base de reconciliação LED-02

Hoje `ImportacaoSCPI` guarda só metadados agregados (`total_linhas`,
`total_novos`, `total_divergentes`) e o SHA-256 do arquivo; os bytes do CSV são
descartados depois da confirmação. Como o bootstrap de saldo do SCPI fica fora
do razão (LED-01, lacuna documentada em ADR-0015), não existe insumo para
reconciliar `Σ delta_fisico` com `saldo_fisico` nas linhas nascidas da
importação — nem manualmente. Este plano arquiva o CSV confirmado e o expõe
para download na tela de histórico, atrás da policy que já existe.

## Escopo

### O que muda

- **`apps/estoque/models.py`** — `ImportacaoSCPI` ganha
  `arquivo = models.FileField('arquivo CSV', upload_to='importacoes_scpi/', blank=True)`.
  `blank=True` porque o campo nunca vem de formulário (só do service) e porque
  linhas criadas antes desta mudança não têm arquivo: a tela precisa distinguir
  "importação legada, sem arquivo" de "arquivo disponível". A docstring da
  classe, que hoje afirma "Não armazena o CSV bruto", é reescrita para descrever
  o contrato novo: o CSV vive no storage, não como coluna do banco.
- **`apps/estoque/services.py`** — `confirmar_importacao_scpi` passa
  `arquivo=ContentFile(conteudo_bytes, name=f'{arquivo_hash}.csv')` no mesmo
  `ImportacaoSCPI.objects.create(...)` já existente, dentro do
  `transaction.atomic()` que já envolve a confirmação. Sem parâmetro novo: os
  bytes já estão em memória na assinatura atual.
  O nome em disco é derivado do hash, não de `arquivo_nome`: o hash já é único
  por importação (constraint no model), o que dispensa sufixo anticolisão do
  storage, e mantém entrada de usuário fora do caminho gravado. O nome original
  continua em `arquivo_nome` e é ele que vai no `Content-Disposition`.
  Falha de escrita no storage levanta a exceção do backend (`OSError` e
  parentes), **não** uma exceção de `apps.core.exceptions`. É deliberado:
  ADR-0011 reserva `ErroDominio` para erro de domínio previsível, e disco cheio
  ou permissão de filesystem é falha de infraestrutura. O efeito no usuário é
  500, não uma mensagem de domínio — `confirmar_importacao_scpi_view` continua
  capturando só `ConflitoDominio` e `DadosInvalidos`. O que o critério de aceite
  exige está garantido: a exceção sobe de dentro do `atomic` e desfaz a
  importação inteira.
- **`config/settings/base.py`** — `MEDIA_ROOT = BASE_DIR / 'media'` e
  `MEDIA_URL = 'media/'`. `media/` já está no `.gitignore`.
- **`config/urls.py`** — **não muda**. Nada de `static(settings.MEDIA_URL, ...)`:
  o download é servido só pela view autenticada. Registrado aqui porque a
  ausência é deliberada, não esquecimento.
- **`config/settings/test.py`** — `MEDIA_ROOT = BASE_DIR / '.pytest-media'`, para
  que a suíte (que já chama `confirmar_importacao_scpi` em dezenas de testes)
  nunca escreva no `media/` do desenvolvedor. Entrada nova no `.gitignore`. O
  diretório é descartável e acumula resíduo entre execuções — inócuo porque
  nenhum teste afirma caminho gravado, e apagável a qualquer momento.
- **`apps/estoque/selectors.py`** — novo `buscar_importacao_scpi(*, importacao_id)`,
  irmão de `buscar_detalhe_saida_excepcional`: devolve a `ImportacaoSCPI` ou
  `None`. A leitura do download vive aqui, não na view.
  `sucesso_importacao_scpi_view`, que hoje faz a mesma leitura pelo ORM direto,
  **não** é refatorada nesta issue — trocar a leitura de uma view que este plano
  não toca é escopo alheio.
- **`apps/estoque/views.py`** — nova `baixar_arquivo_importacao_scpi_view(request, pk)`.
  Decorators na ordem das views irmãs, com `@login_required` **por fora** de
  `@require_http_methods(['GET'])`: assim requisição anônima é redirecionada ao
  login antes de a checagem de método responder, e um POST anônimo vira redirect,
  não `405`. Chama `exigir_pode_consultar_historico_scpi(papel)` e traduz
  `PermissaoNegada` para `PermissionDenied`. A leitura vem do selector acima;
  `None` vira `Http404`.
  São **três** os caminhos de `Http404`: pk inexistente, importação sem arquivo, e
  arquivo ausente no storage. O terceiro é detectado abrindo o `FieldFile`
  (`importacao.arquivo.open('rb')`) dentro de `try/except FileNotFoundError`
  **antes** de montar a resposta — `FileResponse` lê de forma tardia, então sem
  essa abertura antecipada o arquivo sumido estouraria no meio do streaming, como
  500 e com o header já enviado. O handle aberto é passado direto para
  `FileResponse(..., as_attachment=True, filename=<basename de arquivo_nome>)`,
  sem `with`: quem fecha é o `FileResponse`, ao terminar de servir.
- **`apps/estoque/urls.py`** — rota
  `importacao-scpi/<int:pk>/arquivo/` → `baixar_arquivo_importacao_scpi`.
- **`apps/estoque/templates/estoque/historico_importacoes_scpi.html`** — nona
  coluna "Arquivo CSV" com link de download via
  `components/button.html` (`variant="link"`, `size="sm"`, `aria_label` citando o
  nome do arquivo). Importação sem arquivo renderiza um traço com texto
  `sr-only` explicando a ausência, em vez de link morto.

### O que não muda

- **Ledger.** `confirmar_importacao_scpi` continua sem gerar
  `MovimentacaoEstoque` — a lacuna LED-01 de ADR-0015 segue aberta e é escopo de
  outra issue. Este plano entrega o insumo que torna a reconciliação LED-02 do
  bootstrap auditável; não retrofita o bootstrap no razão.
- **Autorização.** Nenhuma policy nova. O download é a mesma capacidade de
  "consultar histórico SCPI" e reusa `pode_consultar_historico_scpi` /
  `exigir_pode_consultar_historico_scpi` (superusuário e chefe de almoxarifado).
  `docs/matriz-permissoes.md` não ganha linha: ela não enumera hoje a consulta ao
  histórico SCPI, e o download não cria capacidade nova.
- **Hash e bloqueio de reimportação.** Cálculo, unicidade e `ConflitoDominio`
  intactos.
- **Fluxo de preview.** O handoff via sessão (`scpi_preview_bytes` em base64) e
  `confirmar_importacao_scpi_view` em `apps/requisicoes/views.py` seguem iguais.
- **Selector de listagem.** `listar_historico_importacoes_scpi` não muda: continua
  `select_related('importado_por', 'estoque')` sem `only()`/`defer()`. O
  `FileField` só carrega um caminho, não o conteúdo.
- **`test_nao_expoe_csv_bruto`** (`apps/estoque/tests/test_selectors.py`) segue
  válido e sem edição. Ele afirma que o item devolvido pelo selector não tem
  atributo `conteudo_csv` — ou seja, que o CSV não virou coluna do banco. Isso
  continua verdade: o conteúdo vai para o storage e o model guarda só o caminho.
- **ADRs.** Nenhuma emenda. ADR-0015 registra a lacuna LED-01 do bootstrap, que
  este plano não fecha; ADR-0011 não é contrariado (ver a nota sobre exceção de
  storage acima). A frase "não armazena o CSV bruto" que muda vive na docstring
  do model, não em ADR.
- **Admin.** `ImportacaoSCPIAdmin` nega add, change e delete, então o campo novo
  não aparece em nenhum formulário. `list_display` fica como está.

## Arquivos tocados

| Arquivo | Mudança |
|---|---|
| `apps/estoque/models.py` | Campo `arquivo` em `ImportacaoSCPI`; docstring reescrita. |
| `apps/estoque/services.py` | `confirmar_importacao_scpi` grava o `ContentFile` no `create`. |
| `apps/estoque/selectors.py` | Novo `buscar_importacao_scpi`. |
| `apps/estoque/views.py` | Nova `baixar_arquivo_importacao_scpi_view`. |
| `apps/estoque/urls.py` | Rota `importacao-scpi/<int:pk>/arquivo/`. |
| `apps/estoque/templates/estoque/historico_importacoes_scpi.html` | Coluna "Arquivo CSV" com link/ausência. |
| `config/settings/base.py` | `MEDIA_ROOT`, `MEDIA_URL`. |
| `config/settings/test.py` | `MEDIA_ROOT` isolado da suíte. |
| `.gitignore` | `.pytest-media/`. |
| `apps/estoque/tests/test_services.py` | 3 testes em `TestConfirmarImportacaoScpi`. |
| `apps/estoque/tests/test_selectors.py` | Classe `TestBuscarImportacaoScpi`. |
| `apps/estoque/tests/test_views.py` | Classe `TestBaixarArquivoImportacaoScpiView` + 2 testes em `TestHistoricoImportacoesScpiView`. |

## Estratégia de testes

Ordem TDD por comportamento, uma fatia vertical de cada vez (service → rota →
tela). Todos os testes que tocam arquivo fixam `settings.MEDIA_ROOT` em
`tmp_path` pela fixture `settings` do pytest-django, para não depender de
resíduo de execução anterior. Nenhum teste afirma o caminho exato gravado no
storage (o backend pode acrescentar sufixo anticolisão); afirmam conteúdo,
sufixo `.csv` e `Content-Disposition`.

**Service (`test_services.py`, em `TestConfirmarImportacaoScpi`):**

- Caminho feliz: confirmação persiste o CSV e `importacao.arquivo.read()`
  devolve exatamente os bytes de entrada.
- Integridade: `hashlib.sha256(importacao.arquivo.read()).hexdigest() == importacao.arquivo_hash`.
- Violação de domínio/infra: falha ao gravar no storage (patch do `_save` do
  backend levantando `OSError`) desfaz a importação inteira — nenhuma
  `ImportacaoSCPI`, nenhum `Material` e nenhum `SaldoEstoque` novo no banco
  depois da exceção. As três tabelas entram na asserção porque as três são
  escritas pelo mesmo `atomic`: verificar só duas deixaria passar um rollback
  parcial.

Permissão negada e estado inválido (reimportação bloqueada) já têm cobertura na
classe e não são duplicados.

**Selector (`test_selectors.py`, `TestBuscarImportacaoScpi`):**

- Importação existente é devolvida pelo pk; pk inexistente devolve `None`.

**Views (`test_views.py`):**

- `TestBaixarArquivoImportacaoScpiView`, autorização e método: GET anônimo →
  redirect para login; POST anônimo → redirect para login (não `405`, o que fixa
  a ordem dos decorators); POST autenticado e autorizado → `405`; solicitante →
  403; auxiliar de almoxarifado → 403.
- Caminho feliz: chefe de almoxarifado → 200 com corpo igual ao CSV e
  `Content-Disposition` exato (`attachment; filename="relatorio.csv"`, asserção
  do header inteiro, não só da presença de `attachment`); superusuário → 200.
- Saneamento do nome: importação cujo `arquivo_nome` traz componentes de caminho
  (`subdir/relatorio.csv`) responde com `filename="relatorio.csv"` — o header usa
  o basename, nunca o caminho recebido.
- Ausências → 404: pk inexistente; importação sem arquivo; e arquivo que consta
  no banco mas foi removido do storage (apagado do `MEDIA_ROOT` no teste), que
  precisa virar 404 e não 500 no meio do streaming.
- `TestHistoricoImportacoesScpiView`: listagem mostra o link de download quando
  há arquivo; não mostra link quando a importação é legada (sem arquivo).

## Invariantes relevantes (`docs/matriz-invariantes.md`)

| Invariante | Efeito |
|---|---|
| **LED-01** | Inalterado. O bootstrap do SCPI continua fora do ledger, como a própria linha da matriz já ressalva. Arquivar o CSV não é mutação de saldo e não gera movimentação. |
| **LED-02** | Definição inalterada. O que muda é a verificabilidade: com o arquivo original preservado, a reconciliação das linhas nascidas do bootstrap deixa de depender de um insumo destruído (achado R8 da auditoria). |
| **LED-05** | Preservado por analogia: o arquivo é escrito uma vez, na confirmação, e nenhuma superfície o reescreve ou apaga (admin nega change e delete). |
| **PER-08** | Reforçado: a view de download chama a mesma `exigir_pode_consultar_historico_scpi` que a tela de histórico. |
| **EST-\*** | Intocados. Nenhuma mutação de saldo entra ou sai. |

## Riscos

1. **Storage não é transacional.** `transaction.atomic` cobre o banco, não o
   filesystem. A direção que o critério de aceite exige está garantida — erro ao
   gravar o arquivo levanta dentro do `atomic` e desfaz a importação inteira —,
   mas a direção inversa não: um rollback posterior (ex.: falha no
   `_pos_importacao_hook`) deixa o arquivo órfão em disco. O órfão é inerte: a
   view só serve arquivo a partir de uma linha existente no banco, e o nome
   determinístico pelo hash faz a importação seguinte do mesmo CSV ganhar sufixo
   próprio em vez de colidir. Limpeza de órfãos não entra nesta issue.
2. **`MEDIA_ROOT` local no piloto.** Filesystem do processo. Se o piloto passar a
   rodar em mais de um host ou container sem volume compartilhado, os downloads
   quebram de forma silenciosa (404 em host errado). Fora de escopo aqui —
   configuração de implantação pertence à trilha de settings do piloto.
3. **Crescimento de disco.** CSVs do SCPI são pequenos (dezenas de KB) e a
   frequência de importação é baixa; sem política de retenção nesta fase.
4. **Migration.** Campo novo em model → o fluxo efêmero do projeto se aplica:
   apagar e recriar as migrations locais via `make setup` antes de rodar a suíte.
5. **Conteúdo servido a partir de upload.** O download responde com
   `as_attachment=True` e nome de arquivo saneado (basename de `arquivo_nome`),
   nunca inline — o CSV não é renderizado no navegador.

## Fora de escopo

- Retrofit do bootstrap SCPI no ledger (LED-01) e implementação automática da
  reconciliação LED-02.
- Backfill de arquivo para importações já registradas — os bytes não existem
  mais.
- Cards mobile / redesenho da tela de histórico.
- Política de retenção, expurgo ou storage remoto (S3 e equivalentes).
