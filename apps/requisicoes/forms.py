"""Formulários server-rendered de requisições."""

from django import forms
from django.db import models

from apps.accounts.models import User
from apps.estoque.models import Material, SaldoEstoque


class CriarRascunhoRequisicaoForm(forms.Form):
    beneficiario = forms.ModelChoiceField(
        label='Beneficiário',
        queryset=User.objects.none(),
    )
    material = forms.ModelChoiceField(
        label='Material',
        queryset=Material.objects.none(),
    )
    quantidade_solicitada = forms.DecimalField(
        label='Quantidade solicitada',
        min_value=0,
        max_digits=12,
        decimal_places=3,
    )
    observacao_geral = forms.CharField(
        label='Observação geral',
        required=False,
        widget=forms.Textarea(attrs={'rows': 3}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['beneficiario'].queryset = User.objects.filter(
            is_active=True,
        ).order_by('nome')
        materiais_com_saldo = SaldoEstoque.objects.filter(
            estoque__ativo=True,
            material__ativo=True,
            saldo_fisico__gt=models.F('saldo_reservado'),
        ).values('material_id')
        self.fields['material'].queryset = Material.objects.filter(
            id__in=materiais_com_saldo,
        ).order_by('nome')
        for field in self.fields.values():
            field.widget.attrs.update(
                {
                    'class': (
                        'mt-2 block w-full rounded-lg border border-slate-300 '
                        'bg-white px-3 py-2 text-sm text-slate-900 shadow-sm '
                        'focus:border-blue-500 focus:outline-none '
                        'focus:ring-2 focus:ring-blue-500'
                    )
                }
            )

    def clean_quantidade_solicitada(self):
        quantidade = self.cleaned_data['quantidade_solicitada']
        if quantidade <= 0:
            raise forms.ValidationError(
                'A quantidade solicitada deve ser maior que zero.',
                code='quantidade_invalida',
            )
        return quantidade
