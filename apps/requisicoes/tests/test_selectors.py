"""Testes unitários para seletores de requisições."""

import pytest

from apps.requisicoes.selectors import material_eh_elegivel, materiais_para_requisicao


@pytest.mark.django_db
def test_materiais_para_requisicao_inclui_disponivel(material_disponivel):
    assert material_disponivel in materiais_para_requisicao()


@pytest.mark.django_db
def test_materiais_para_requisicao_exclui_inativo(material_inativo):
    assert material_inativo not in materiais_para_requisicao()


@pytest.mark.django_db
def test_materiais_para_requisicao_exclui_sem_saldo(material_sem_saldo):
    assert material_sem_saldo not in materiais_para_requisicao()


@pytest.mark.django_db
def test_materiais_para_requisicao_exclui_divergente(material_divergente):
    assert material_divergente not in materiais_para_requisicao()


@pytest.mark.django_db
def test_material_eh_elegivel_true_se_disponivel(material_disponivel):
    assert material_eh_elegivel(material_disponivel)


@pytest.mark.django_db
def test_material_eh_elegivel_false_se_inativo(material_inativo):
    assert not material_eh_elegivel(material_inativo)


@pytest.mark.django_db
def test_material_eh_elegivel_false_se_sem_saldo(material_sem_saldo):
    assert not material_eh_elegivel(material_sem_saldo)


@pytest.mark.django_db
def test_material_eh_elegivel_false_se_divergente(material_divergente):
    assert not material_eh_elegivel(material_divergente)
