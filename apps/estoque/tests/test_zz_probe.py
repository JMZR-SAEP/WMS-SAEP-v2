import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse


CSV = b'CADPRO;DENOMINACAO;QUAN3\n000.888.060;Teste;10.000\n'


@pytest.mark.django_db
def test_probe_sem_estoque_ativo(client, superuser):
    from apps.estoque.models import Estoque

    url_preview = reverse('estoque:preview_importacao_scpi')
    url = reverse('requisicoes:confirmar_importacao_scpi')
    client.force_login(superuser)
    arquivo = SimpleUploadedFile('seed.csv', CSV, content_type='text/csv')
    client.post(url_preview, {'arquivo': arquivo})
    print('ESTOQUES:', Estoque.objects.count())
    print('SESSAO TEM PREVIEW:', 'scpi_preview_bytes' in client.session)
    Estoque.objects.update(ativo=False)
    resp = client.post(url, {}, HTTP_HX_REQUEST='true')
    print('STATUS:', resp.status_code)
    corpo = resp.content.decode()
    print('TEM "pre-visualizacao":', 'visualiza' in corpo)
    print('TEM "estoque ativo":', 'estoque ativo' in corpo)
