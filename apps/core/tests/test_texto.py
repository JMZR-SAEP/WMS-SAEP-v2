"""Normalização de texto para apresentação — `sentence_case`."""

import pytest

from apps.core.texto import sentence_case


@pytest.mark.parametrize(
    ('entrada', 'esperado'),
    [
        # ALL-CAPS do SCPI vira sentence case
        ('LIXA D AGUA GRAO 220', 'Lixa d agua grao 220'),
        ('SILICONE ACETICO TRANSPARENTE 280G', 'Silicone acetico transparente 280g'),
        # já em sentence case: idempotente
        ('Eletroduto rígido roscável 3/4"', 'Eletroduto rígido roscável 3/4"'),
        # o que `str.title()`/`|title` quebrariam permanece intacto
        ('Cabo 3/4" preto', 'Cabo 3/4" preto'),
        ('Parafuso 280G', 'Parafuso 280g'),
        # inicial não alfabética: sobe a primeira letra de fato
        ('3/4" CANO PVC', '3/4" Cano pvc'),
        # sem letra nenhuma (ex.: fallback para CADPRO numérico)
        ('000.000.220', '000.000.220'),
        # vazio / None
        ('', ''),
        (None, ''),
    ],
)
def test_sentence_case(entrada, esperado):
    assert sentence_case(entrada) == esperado


def test_sentence_case_e_idempotente():
    uma_vez = sentence_case('SILICONE ACETICO 280G')
    assert sentence_case(uma_vez) == uma_vez
