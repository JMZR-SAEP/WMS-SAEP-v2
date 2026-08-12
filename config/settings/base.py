"""Configurações comuns do projeto WMS-SAEP.

Valores sensíveis e específicos de ambiente vêm de variáveis de ambiente
(arquivo ``.env``), lidas via django-environ. Não há fallback para SQLite:
``DATABASE_URL`` deve apontar para um PostgreSQL.
"""

from datetime import timedelta
from pathlib import Path

import environ

# Raiz do projeto: config/settings/base.py -> sobe três níveis.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, []),
)
environ.Env.read_env(BASE_DIR / '.env')

SECRET_KEY = env('SECRET_KEY')
DEBUG = env('DEBUG')
ALLOWED_HOSTS = env('ALLOWED_HOSTS')


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Terceiros
    'axes',
    'django_htmx',
    # Apps de domínio
    'apps.accounts',
    'apps.estoque',
    'apps.requisicoes',
    'apps.notificacoes',
    # Camada compartilhada de UI
    'apps.core',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_htmx.middleware.HtmxMiddleware',
    # Precisa ser o último: age na fase de resposta, só para trocar a resposta
    # de uma tentativa de login já bloqueada pela página de bloqueio.
    'axes.middleware.AxesMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'apps.requisicoes.context_processors.flags_de_papel',
                'apps.notificacoes.context_processors.notificacoes_ctx',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# Database — sem fallback silencioso; exige DATABASE_URL (PostgreSQL).
DATABASES = {
    'default': env.db('DATABASE_URL'),
}


# Password validation

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

AUTH_USER_MODEL = 'accounts.User'

LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = 'core:home'


# Lockout de login — django-axes (ADR-0018)
#
# O login por matrícula é a única porta do sistema, e o namespace de matrículas
# é curto e adivinhável (`OBRAS001`, `ALMOX001`). Sem lockout, força bruta custa
# só largura de banda. Nada disso vive na view nem no formulário: entra por
# backend de autenticação mais middleware.

AUTHENTICATION_BACKENDS = [
    # Primeiro da lista de propósito: é ele que aborta a autenticação de um
    # cliente já bloqueado, antes de qualquer verificação de senha.
    'axes.backends.AxesStandaloneBackend',
    'django.contrib.auth.backends.ModelBackend',
]

# O default do axes é `get_user_model().USERNAME_FIELD`, que aqui seria
# `matricula`. Mas quem posta é o `AuthenticationForm` do Django, cujo campo se
# chama sempre `username` — é essa a chave que chega em `request.POST` e no
# `credentials` de `authenticate()`. Sem esta linha o axes procuraria
# `matricula`, não acharia, e agruparia as falhas sob `(None, ip_address)`: um
# balde por IP, com a matrícula fora da chave, em que erros de pessoas
# diferentes se somam e trancam todas elas.
AXES_USERNAME_FORM_FIELD = 'username'

# Lista aninhada = bloqueia a *combinação* matrícula+IP. A forma plana
# (`['username', 'ip_address']`) bloquearia por matrícula OU por IP, o que
# deixaria qualquer um trancar a conta alheia de qualquer lugar.
AXES_LOCKOUT_PARAMETERS = [['username', 'ip_address']]

AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = timedelta(minutes=15)

# Janela deslizante: tentativa expirada deixa de contar, em vez de acumular
# para sempre.
AXES_USE_ATTEMPT_EXPIRATION = True

# Quem prova saber a própria senha zera o contador. É o que impede que erros
# esparsos ao longo do dia somem até trancar um usuário legítimo.
AXES_RESET_ON_SUCCESS = True

# Default do pacote, declarado por ser decisão de segurança: cada tentativa
# durante o bloqueio reinicia os 15 minutos. Com IP real por cliente isso só
# prolonga o bloqueio de quem ataca.
AXES_RESET_COOL_OFF_ON_FAILURE_DURING_LOCKOUT = True

# Sem isto não há trilha auditável: `AccessAttempt` é agregado e some no
# primeiro login bem-sucedido, por causa de `AXES_RESET_ON_SUCCESS`. O
# crescimento é limitado por `AXES_ACCESS_FAILURE_LOG_PER_USER_LIMIT` (1000).
AXES_ENABLE_ACCESS_FAILURE_LOG = True

AXES_ENABLE_RETRY_AFTER_HEADER = True
AXES_LOCKOUT_TEMPLATE = 'accounts/login_bloqueado.html'


# Internationalization

LANGUAGE_CODE = 'pt-br'

TIME_ZONE = 'America/Sao_Paulo'

USE_I18N = True

USE_TZ = True


# Static files

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'


# Media files — CSVs arquivados da importação SCPI.
#
# `MEDIA_URL` existe porque o Django o exige para `FileField.url`, não porque
# haja rota servindo `MEDIA_ROOT`: `config/urls.py` não publica esse diretório.
# O download passa por view autenticada, atrás da policy do histórico SCPI.

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'


# Default primary key field type

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
