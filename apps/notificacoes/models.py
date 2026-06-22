from django.conf import settings
from django.db import models


class TipoNotificacao(models.TextChoices):
    AUTORIZACAO = 'autorizacao', 'Autorização'
    RECUSA = 'recusa', 'Recusa'
    ATENDIMENTO = 'atendimento', 'Atendimento'
    DIVERGENCIA_ESTOQUE = 'divergencia_estoque', 'Divergência de estoque'


class Notificacao(models.Model):
    destinatario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notificacoes',
        verbose_name='destinatário',
    )
    tipo = models.CharField(
        max_length=30,
        choices=TipoNotificacao.choices,
        verbose_name='tipo',
    )
    requisicao_id = models.IntegerField(
        verbose_name='requisição',
        null=True,
        blank=True,
    )
    lida = models.BooleanField(default=False, verbose_name='lida')
    criado_em = models.DateTimeField(auto_now_add=True, verbose_name='criado em')

    class Meta:
        verbose_name = 'notificação'
        verbose_name_plural = 'notificações'
        ordering = ['-criado_em']
        indexes = [
            models.Index(fields=['destinatario', 'lida', 'criado_em']),
        ]

    def __str__(self) -> str:
        return f'{self.get_tipo_display()} → {self.destinatario}'
