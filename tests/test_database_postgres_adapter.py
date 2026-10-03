from database import is_postgres_url, normalize_pg_url, PostgresCursorWrapper
from config import Config


def test_is_postgres_url_detection():
    assert is_postgres_url('postgresql://user:pass@host:6543/db') is True
    assert is_postgres_url('postgres://user:pass@host:5432/db') is True
    assert is_postgres_url('sqlite:///banco.db') is False
    assert is_postgres_url('banco.db') is False
    assert is_postgres_url('') is False
    assert is_postgres_url(None) is False


def test_normalize_pg_url_sslmode_and_scheme():
    # 1. Garante sslmode=require se ausente
    url1 = 'postgresql://postgres.cxxknecvqvmyrveralmx:secret@aws-0-sa-east-1.pooler.supabase.com:6543/postgres'
    normalized1 = normalize_pg_url(url1)
    assert 'sslmode=require' in normalized1
    assert normalized1.startswith('postgresql://')

    # 2. Converte scheme de postgres:// para postgresql://
    url2 = 'postgres://postgres.cxxknecvqvmyrveralmx:secret@aws-0-sa-east-1.pooler.supabase.com:6543/postgres'
    normalized2 = normalize_pg_url(url2)
    assert normalized2.startswith('postgresql://')
    assert 'sslmode=require' in normalized2

    # 3. Preserva sslmode existente
    url3 = 'postgresql://user:pass@host:6543/db?sslmode=verify-full'
    normalized3 = normalize_pg_url(url3)
    assert 'sslmode=verify-full' in normalized3


class DummyRealCursor:
    def __init__(self):
        self.executed_sql = None
        self.executed_params = None

    def execute(self, sql, params=None):
        self.executed_sql = sql
        self.executed_params = params

    def fetchone(self):
        return {'id': 42}

    def fetchall(self):
        return [{'id': 42, 'nome': 'Teste'}]

    def close(self):
        pass


def test_postgres_cursor_wrapper_translation():
    dummy = DummyRealCursor()
    wrapper = PostgresCursorWrapper(dummy)

    # 1. Converte ? para %s
    wrapper.execute('SELECT * FROM produtos WHERE id = ? AND organization_id = ?', (10, 1))
    assert dummy.executed_sql == 'SELECT * FROM produtos WHERE id = %s AND organization_id = %s'
    assert dummy.executed_params == (10, 1)

    # 2. BEGIN IMMEDIATE vira no-op
    dummy.executed_sql = None
    wrapper.execute('BEGIN IMMEDIATE')
    assert dummy.executed_sql is None

    # 3. INSERT sem RETURNING adiciona RETURNING id e preenche lastrowid
    wrapper.execute('INSERT INTO categorias (nome) VALUES (?)', ('Bebidas',))
    assert 'RETURNING id' in dummy.executed_sql
    assert '%s' in dummy.executed_sql
    assert wrapper.lastrowid == 42


def test_config_database_url_precedence(monkeypatch):
    test_url = 'postgresql://test:pass@pooler.supabase.com:6543/db?sslmode=require'
    monkeypatch.setenv('DATABASE_URL', test_url)
    
    # Recarrega ou avalia precedence
    from importlib import reload
    import config
    reload(config)
    assert config.Config.DATABASE_URL == test_url
    assert config.Config.DATABASE == test_url
