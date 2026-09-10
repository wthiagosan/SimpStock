import os
import tempfile
import pytest
from app import create_app
from database import init_db
from config import Config


class TestConfig(Config):
    TESTING = True
    DEBUG = False
    SECRET_KEY = 'test-secret-key'
    JWT_SECRET = 'test-jwt-secret'
    JWT_EXPIRATION_HOURS = 2


@pytest.fixture(scope='function')
def temp_db_path():
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    yield path
    if os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            pass


@pytest.fixture
def app(temp_db_path):
    TestConfig.DATABASE = temp_db_path
    init_db(temp_db_path)
    app = create_app(TestConfig)
    return app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def admin_headers(client):
    # Faz login com admin padrão
    res = client.post('/login', json={
        'email': 'admin@simpstock.com',
        'senha': 'admin123'
    })
    token = res.get_json()['token']
    return {'Authorization': f'Bearer {token}'}


@pytest.fixture
def user_headers(client):
    # Cria e loga com usuário de teste
    client.post('/register', json={
        'nome': 'Lojista Teste',
        'email': 'lojista@teste.com',
        'senha': 'Senha123'
    })
    res = client.post('/login', json={
        'email': 'lojista@teste.com',
        'senha': 'Senha123'
    })
    token = res.get_json()['token']
    return {'Authorization': f'Bearer {token}'}
