"""Storage de estáticos do piloto: hash no nome, sem tropeçar na fonte do Tailwind.

`ManifestStaticFilesStorage` reescreve as URLs encontradas dentro dos arquivos
CSS coletados. `apps/core/static/core/css/input.css` é a **fonte** do Tailwind,
não um asset servido: ele começa com `@import "tailwindcss"`, que não é um
caminho de arquivo, e o `collectstatic` morria com

    ValueError: The file 'core/css/tailwindcss' could not be found

O artefato servido é o `app.css` compilado (`make css-build`), e é ele que
precisa de hash. A fonte é coletada só porque vive dentro de `static/` — onde
está por conveniência do CLI do Tailwind, que aponta para lá.

A alternativa seria mover `input.css` para fora da árvore de estáticos. Ela é
melhor a longo prazo e ficou de fora aqui de propósito: mexeria no `Makefile`,
no `test_tokens_semanticos.py` e na documentação do design system, tudo por um
ganho que este arquivo entrega em cinco linhas.
"""

from django.contrib.staticfiles.storage import ManifestStaticFilesStorage


class EstaticosComHash(ManifestStaticFilesStorage):
    """Igual ao padrão, menos o pós-processamento da fonte do Tailwind."""

    #: Caminhos (relativos a `STATIC_ROOT`) que entram no manifesto sem passar
    #: pela reescrita de URLs. Só a fonte do Tailwind, por ora.
    NAO_REESCREVER = ('core/css/input.css',)

    def post_process(self, paths, dry_run=False, **options):
        restantes = {
            caminho: valor
            for caminho, valor in paths.items()
            if caminho not in self.NAO_REESCREVER
        }
        yield from super().post_process(restantes, dry_run, **options)
