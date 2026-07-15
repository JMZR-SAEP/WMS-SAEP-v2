# Plano — Issue #81: sistema de ícones `{% icon %}` com catálogo vendorizado

Épico: #68 (extração de componentes do design system, Fase 3).

## Escopo

### Dentro do escopo

- Template tag `{% icon name size=20 class="..." %}` em `apps/core/templatetags/core_tags.py`.
- Catálogo vendorizado: um SVG completo por arquivo em
  `apps/core/templates/components/icons/<nome>.svg`, sempre com `aria-hidden="true"`.
- Migração dos ícones repetidos ≥2× confirmados por grep no código atual (contagens do
  épico eram de uma auditoria anterior; recontadas aqui diretamente no código):

  | Nome no catálogo | Ocorrências atuais | Arquivos |
  |---|---|---|
  | `voltar` (back-arrow) | 6 | `copiar_confirmacao.html`, `rascunho_form.html` (×2), `atender_retirada.html`, `detalhe.html`, `nova_saida_excepcional.html` |
  | `lixeira` (variante modal de confirmação de exclusão) | 2 | `_modal_icon.html` (variant="danger"), `detalhe.html` |
  | `remover` (variante de remover linha de item) | 2 | `_item_form_row.html`, `nova_saida_excepcional.html` |
  | `spinner` | 4 | `autocomplete.html`, `preview_importacao_scpi.html` (×3) |
  | `adicionar` (plus) | 2 | `rascunho_form.html`, `nova_saida_excepcional.html` |
  | `enviar` (send) | 2 | `detalhe.html`, `rascunho_form.html` |
  | `copiar` (copy) | 2 | `copiar_confirmacao.html`, `detalhe.html` |

- Testes unitários da tag em `apps/core/tests/test_icons.py`.

### Fora do escopo (decisões explícitas)

1. **`lixeira` vs `remover` são dois ícones distintos, não um só.** O épico rotula
   ambos como "lixeira ×4", mas são dois desenhos SVG visualmente diferentes (path
   diferente). Unificá-los sob um nome quebraria o critério de aceite "zero mudança
   visual". Cada um vira um arquivo próprio no catálogo.
2. **Contagem de `plus`**: o épico diz ×3; a recontagem via grep no código atual
   encontra 2 ocorrências reais (`rascunho_form.html`, `nova_saida_excepcional.html`).
   Tratado como ruído de auditoria antiga, não como mudança de escopo — migram-se as
   2 ocorrências reais.
3. **Ícones de navegação** (`ICONES`/`secoes_navegacao` em `core_tags.py`, usados por
   `_side_nav.html`/`_topbar_nav.html`, issue #80 já mesclada) **não migram nesta
   fatia**. Já não há duplicação de path SVG ali — cada ícone é definido uma vez no
   dict `ICONES` e reutilizado por chave; migrar para o novo catálogo não reduziria
   duplicação nenhuma e tocaria uma feature de nav recém-entregue sem necessidade.
4. **`components/icons/_check.html` e `_seta_circular.html`** (partials pré-existentes,
   só `<path>` sem `<svg>` wrapper, incluídos hoje via `icon_template` do
   `button.html` e `icone` do `empty_state.html`) **não migram**. Já são fonte única
   (sem duplicação) e usam mecanismo diferente (include de fragmento cru). Mexer
   neles arrisca regressão em #71/#76 sem ganho de deduplicação.
5. **SVGs de uso único** (ex.: ícone do `base_auth.html`, ícones de status internos
   de `_modal_body.html`/`_modal_icon.html` variant info/warning que não se repetem
   fora desse componente) permanecem inline, conforme a issue permite.

## Arquivos tocados

**Novos:**
- `apps/core/templates/components/icons/voltar.svg`
- `apps/core/templates/components/icons/lixeira.svg`
- `apps/core/templates/components/icons/remover.svg`
- `apps/core/templates/components/icons/spinner.svg`
- `apps/core/templates/components/icons/adicionar.svg`
- `apps/core/templates/components/icons/enviar.svg`
- `apps/core/templates/components/icons/copiar.svg`
- `apps/core/tests/test_icons.py`

**Modificados:**
- `apps/core/templatetags/core_tags.py` — nova tag `icon`.
- `apps/core/templates/components/_modal_icon.html` — variant danger usa `{% icon "lixeira" %}`.
- `apps/core/templates/components/autocomplete.html` — spinner sem `x-show`.
- `apps/estoque/templates/estoque/preview_importacao_scpi.html` — 3 spinners; os 2 com
  `x-show="enviando"`/`x-show="confirmando"` passam a envolver a tag num `<span
  x-show="...">` (a diretiva Alpine sai do `<svg>` para o `<span>` pai, sem alterar
  layout: já é o único filho do `<button>` num flex `gap-2`).
- `apps/estoque/templates/estoque/nova_saida_excepcional.html` — voltar, remover, adicionar.
- `apps/requisicoes/templates/requisicoes/partials/_item_form_row.html` — remover.
- `apps/requisicoes/templates/requisicoes/rascunho_form.html` — voltar ×2, adicionar, enviar.
- `apps/requisicoes/templates/requisicoes/atender_retirada.html` — voltar.
- `apps/requisicoes/templates/requisicoes/detalhe.html` — voltar, lixeira, copiar, enviar.
- `apps/requisicoes/templates/requisicoes/copiar_confirmacao.html` — voltar, copiar.

Nenhum arquivo de `services.py`, `policies.py`, `selectors.py` ou `models.py` é tocado.

## Design da tag

```python
@register.simple_tag
def icon(name: str, size: int = 20, **kwargs: str) -> str:
    css_class = kwargs.get('class', '')
    try:
        return mark_safe(
            render_to_string(
                f'components/icons/{name}.svg',
                {'size': size, 'class': css_class},
            )
        )
    except TemplateDoesNotExist as exc:
        raise ImproperlyConfigured(
            f"Ícone \"{name}\" não encontrado em components/icons/. "
            'Confira o nome ou adicione o arquivo ao catálogo.'
        ) from exc
```

- `class` chega via `**kwargs` porque `class` é palavra reservada em Python — não dá
  para declarar como parâmetro nomeado, mas o Django simple_tag aceita perfeitamente
  `{% icon "x" class="h-4 w-4" %}` porque a chamada é feita com `**kwargs` internamente.
- Cada arquivo `.svg` do catálogo usa `{{ size }}`/`{{ class }}` só onde o markup
  original variava; onde o original é 100% fixo (ex.: `voltar` nunca teve `class`
  atribuído em nenhuma das 6 ocorrências), o arquivo não referencia essas variáveis.
- Erro de nome inexistente vira `ImproperlyConfigured` com mensagem clara, seguindo o
  padrão já usado em `validar_contrato_modal` no mesmo arquivo.

## Estratégia de teste

`apps/core/tests/test_icons.py` (sem DB, mesmo padrão de `test_components.py`):

- **Caminho feliz**: renderizar cada um dos 7 ícones e comparar contra o markup
  original capturado (path `d=` exato, `viewBox`, `aria-hidden="true"`).
- **Parâmetro `class`**: passar `class="h-4 w-4 foo"` e conferir que aparece
  verbatim na saída.
- **Parâmetro `size`** (ícone `voltar`, único que usa `width`/`height`): `size=24`
  muda os atributos `width`/`height` sem alterar o `viewBox` (que é fixo em 24,
  grid nativo do ícone).
- **Erro de nome inexistente**: `{% icon "nao-existe" %}` levanta
  `ImproperlyConfigured` com mensagem citando o nome do ícone.
- **Spinner**: saída contém os dois elementos internos (`circle` + `path`) e
  repassa `animate-spin motion-reduce:animate-none` via `class`.

Verificação nas telas tocadas (não há screenshot-diff automatizado no repo — ADR-0010
não prevê isso):
- Suite completa não deve quebrar (nenhum teste existente hoje faz assert em path
  SVG cru — confirmado por grep antes de escrever este plano).
- Checagem manual via browser preview em pelo menos: `requisicoes/detalhe`,
  `requisicoes/rascunho_form` (nova requisição), `estoque/preview_importacao_scpi`.

## Invariantes

`docs/matriz-invariantes.md` não tem entradas sobre frontend/ícones/templates — é
focado em regras de domínio (transições de requisição, estoque). Nenhuma linha da
matriz se aplica a esta mudança, que é puramente de apresentação e não toca
`services`/`policies`/`selectors`.

## Riscos

- **Regressão visual no spinner com `x-show`**: mitigada movendo a diretiva para um
  `<span>` wrapper que já seria o único filho do flex container — sem mudança de
  `gap`/alinhamento esperada, mas será conferida manualmente no browser preview.
- **`class=""` vazio no markup**: ícones que nunca receberam `class` (ex. `voltar`)
  vão renderizar `class=""` se o parâmetro não for passado, em vez de omitir o
  atributo. Efeito no DOM é nulo (atributo vazio não muda estilo/comportamento), mas
  o arquivo do ícone usa `{% if class %}` para evitar emitir o atributo à toa.
- **Divergência de contagem do épico** (`plus ×3` vs 2 reais): documentada acima,
  não é um risco de execução, só uma nota de rastreabilidade.
