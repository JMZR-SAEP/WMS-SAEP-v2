"""Normalização de texto para apresentação — infraestrutura pura (ADR-0011).

Sem domínio, sem Django: transforma string em string.
"""

from __future__ import annotations


def sentence_case(texto: str | None) -> str:
    """Devolve ``texto`` com a primeira letra maiúscula e o restante minúsculo.

    Uso na fonte: a denominação do SCPI chega em CAIXA ALTA
    (``LIXA D AGUA GRAO 220``) e a Regra da Caixa Alta Estrutural do
    ``DESIGN.md`` proíbe nome de material em maiúsculas. A importação normaliza
    **na escrita** — grava ``Material.nome`` já em sentence case — porque o CSV
    do SCPI é registro de origem e não deve ditar a tipografia do catálogo.

    Por que não ``str.title()`` nem o filtro ``|title`` do Django: ambos sobem a
    inicial de *cada* palavra e a letra que segue qualquer caractere não
    alfabético. Isso quebra ``Eletroduto rígido roscável 3/4"`` (viraria
    ``3/4"``... com a aspa promovendo a próxima letra) e ``280G`` (a letra após
    o dígito seria mantida/subida). Aqui só a primeira letra da string inteira
    sobe.

    Por que não ``django.utils.text.capfirst`` sozinho: ele apenas sobe o
    primeiro caractere e preserva o resto — deixaria ``SILICONE ACETICO
    TRANSPARENTE 280G`` como ``SILICONE ...``. Precisamos baixar o ALL-CAPS que
    aparece no meio, então minusculamos tudo antes de subir a inicial.

    String vazia ou ``None`` devolvem ``''``.
    """
    if not texto:
        return ''
    minusculo = texto.lower()
    for indice, caractere in enumerate(minusculo):
        if caractere.isalpha():
            return minusculo[:indice] + caractere.upper() + minusculo[indice + 1 :]
    return minusculo
