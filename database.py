import os
import re
import sqlite3
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from flask import g, current_app
from werkzeug.security import generate_password_hash
from config import Config

try:
    import psycopg2
    import psycopg2.extras
    from psycopg2 import pool
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False
    psycopg2 = None

_pg_pool = None


def is_postgres_url(url: str) -> bool:
    """Verifica se a string de conexão representa um banco PostgreSQL/Supabase."""
    if not url or not isinstance(url, str):
        return False
    return url.strip().startswith(('postgresql://', 'postgres://'))


def normalize_pg_url(url: str) -> str:
    """Normaliza o esquema e garante o parâmetro sslmode=require para conexão com Supabase."""
    url = url.strip()
    if url.startswith('postgres://'):
        url = 'postgresql://' + url[len('postgres://'):]
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    # Supabase (especialmente o pooler Supavisor na porta 6543) exige SSL obrigatório
    if 'sslmode' not in qs:
        qs['sslmode'] = ['require']
    new_query = urlencode(qs, doseq=True)
    return urlunparse(parsed._replace(query=new_query))


def get_pg_pool(database_url: str):
    """Gerencia um ThreadedConnectionPool resiliente para o Connection Pooling do Supabase (porta 6543)."""
    global _pg_pool
    if _pg_pool is None or _pg_pool.closed:
        dsn = normalize_pg_url(database_url)
        # minconn=1, maxconn=10: ideal para concorrência de Cloud Run e pooler Supavisor
        _pg_pool = pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=10,
            dsn=dsn,
            connect_timeout=10,
            keepalives=1,
            keepalives_idle=30,
            keepalives_interval=10,
            keepalives_count=5
        )
    return _pg_pool


class PostgresCursorWrapper:
    """Wrapper para compatibilizar chamadas de cursor entre SQLite e PostgreSQL/psycopg2."""
    def __init__(self, real_cursor):
        self._cursor = real_cursor
        self.lastrowid = None

    def execute(self, sql, params=None):
        clean_sql = sql.strip()
        # BEGIN IMMEDIATE é comando específico do SQLite; no PostgreSQL transações já são ACID nativas
        if clean_sql.upper() == 'BEGIN IMMEDIATE':
            return self

        # Converte placeholders ? para %s do psycopg2
        clean_sql = clean_sql.replace('?', '%s')

        # Intercepta INSERT sem RETURNING para capturar lastrowid automaticamente no Postgres
        is_insert = clean_sql.upper().startswith('INSERT INTO')
        has_returning = ' RETURNING ' in clean_sql.upper()
        if is_insert and not has_returning:
            clean_sql += ' RETURNING id'
            self._cursor.execute(clean_sql, params or ())
            try:
                ret = self._cursor.fetchone()
                if ret:
                    if isinstance(ret, dict):
                        self.lastrowid = ret.get('id')
                    elif isinstance(ret, (list, tuple)):
                        self.lastrowid = ret[0]
            except Exception:
                self.lastrowid = None
            return self

        self._cursor.execute(clean_sql, params or ())
        return self

    def fetchone(self):
        row = self._cursor.fetchone()
        return dict(row) if row else None

    def fetchall(self):
        rows = self._cursor.fetchall()
        return [dict(r) for r in rows]

    @property
    def description(self):
        return self._cursor.description

    def close(self):
        self._cursor.close()

    def __iter__(self):
        return iter(self.fetchall())


class PostgresConnectionWrapper:
    """Wrapper para a conexão PostgreSQL obtida do pool Supabase."""
    def __init__(self, raw_conn, from_pool=None):
        self._conn = raw_conn
        self._from_pool = from_pool

    def execute(self, sql, params=None):
        cursor = self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        wrapper = PostgresCursorWrapper(cursor)
        return wrapper.execute(sql, params)

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        if self._from_pool and not self._from_pool.closed:
            try:
                self._from_pool.putconn(self._conn)
            except Exception:
                pass
        else:
            try:
                self._conn.close()
            except Exception:
                pass


def get_db(db_path=None):
    """Retorna ou reutiliza a conexão para o ciclo da requisição atual (PostgreSQL/Supabase via DATABASE_URL ou SQLite local)."""
    if db_path is not None:
        target_db = db_path
    else:
        try:
            target_db = (
                current_app.config.get('DATABASE_URL')
                or current_app.config.get('DATABASE')
                or Config.DATABASE_URL
                or Config.DATABASE
            )
        except RuntimeError:
            target_db = Config.DATABASE_URL or Config.DATABASE

    if 'db' not in g:
        if is_postgres_url(target_db):
            if not HAS_PSYCOPG2:
                raise RuntimeError("Driver psycopg2 não encontrado para conectar ao PostgreSQL/Supabase.")
            pg_pool = get_pg_pool(target_db)
            raw_conn = pg_pool.getconn()
            g.db = PostgresConnectionWrapper(raw_conn, from_pool=pg_pool)
        else:
            g.db = sqlite3.connect(target_db, timeout=30.0, isolation_level=None)
            g.db.row_factory = sqlite3.Row
            g.db.execute("PRAGMA foreign_keys = ON")
            g.db.execute("PRAGMA busy_timeout = 30000")
    return g.db


def close_db(error=None):
    """Fecha ou devolve a conexão ao pool ao finalizar a requisição."""
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db(db_path=None):
    """Inicializa as tabelas no PostgreSQL/Supabase ou SQLite com isolamento multi-tenant, índices e restrições de estoque."""
    if db_path is not None:
        target_db = db_path
    else:
        try:
            target_db = (
                current_app.config.get('DATABASE_URL')
                or current_app.config.get('DATABASE')
                or Config.DATABASE_URL
                or Config.DATABASE
            )
        except RuntimeError:
            target_db = Config.DATABASE_URL or Config.DATABASE

    if is_postgres_url(target_db):
        _init_postgres_db(target_db)
    else:
        _init_sqlite_db(target_db)


def _init_postgres_db(target_db):
    """Inicializa tabelas e seeds no PostgreSQL / Supabase."""
    if not HAS_PSYCOPG2:
        raise RuntimeError("Driver psycopg2 não encontrado para inicializar PostgreSQL.")

    dsn = normalize_pg_url(target_db)
    conn = psycopg2.connect(dsn)
    conn.autocommit = True
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id            BIGSERIAL    PRIMARY KEY,
            nome          VARCHAR(100) NOT NULL,
            email         VARCHAR(150) NOT NULL UNIQUE,
            senha         VARCHAR(255) NOT NULL,
            is_admin      BOOLEAN      NOT NULL DEFAULT FALSE,
            is_superadmin BOOLEAN      NOT NULL DEFAULT FALSE,
            criado_em     TIMESTAMPTZ  NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS organizations (
            id                BIGSERIAL    PRIMARY KEY,
            nome              VARCHAR(150) NOT NULL,
            slug              VARCHAR(80)  NOT NULL UNIQUE,
            cnpj_ou_documento VARCHAR(30)      NULL,
            plano             VARCHAR(50)  NOT NULL DEFAULT 'enterprise',
            ativo             BOOLEAN      NOT NULL DEFAULT TRUE,
            criado_em         TIMESTAMPTZ  NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS user_organizations (
            id              BIGSERIAL   PRIMARY KEY,
            usuario_id      BIGINT      NOT NULL REFERENCES usuarios (id) ON DELETE CASCADE ON UPDATE CASCADE,
            organization_id BIGINT      NOT NULL REFERENCES organizations (id) ON DELETE CASCADE ON UPDATE CASCADE,
            role            VARCHAR(50) NOT NULL DEFAULT 'org_operator' CHECK (role IN ('superadmin', 'org_admin', 'org_operator', 'viewer')),
            ativo           BOOLEAN     NOT NULL DEFAULT TRUE,
            criado_em       TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT uq_user_org UNIQUE (usuario_id, organization_id)
        );

        CREATE TABLE IF NOT EXISTS categories (
            id              BIGSERIAL    PRIMARY KEY,
            organization_id BIGINT       NOT NULL REFERENCES organizations (id) ON DELETE CASCADE ON UPDATE CASCADE,
            nome            VARCHAR(100) NOT NULL,
            descricao       VARCHAR(255)     NULL,
            criado_em       TIMESTAMPTZ  NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT uq_cat_org_nome UNIQUE (organization_id, nome)
        );

        CREATE TABLE IF NOT EXISTS suppliers (
            id              BIGSERIAL    PRIMARY KEY,
            organization_id BIGINT       NOT NULL REFERENCES organizations (id) ON DELETE CASCADE ON UPDATE CASCADE,
            nome            VARCHAR(150) NOT NULL,
            contato         VARCHAR(100)     NULL,
            email           VARCHAR(150)     NULL,
            telefone        VARCHAR(50)      NULL,
            criado_em       TIMESTAMPTZ  NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS produtos (
            id              BIGSERIAL      PRIMARY KEY,
            usuario_id      BIGINT         NOT NULL REFERENCES usuarios (id) ON DELETE RESTRICT ON UPDATE CASCADE,
            organization_id BIGINT             NULL REFERENCES organizations (id) ON DELETE CASCADE ON UPDATE CASCADE,
            categoria_id    BIGINT             NULL REFERENCES categories (id) ON DELETE SET NULL ON UPDATE CASCADE,
            fornecedor_id   BIGINT             NULL REFERENCES suppliers (id) ON DELETE SET NULL ON UPDATE CASCADE,
            nome            VARCHAR(150)   NOT NULL,
            marca           VARCHAR(100)   NOT NULL,
            validade        DATE               NULL,
            codigo          VARCHAR(80)    NOT NULL,
            quantidade      INTEGER        NOT NULL DEFAULT 0 CHECK (quantidade >= 0),
            estoque_minimo  INTEGER        NOT NULL DEFAULT 5,
            custo_unitario  NUMERIC(12, 2) NOT NULL DEFAULT 0.0,
            preco_venda     NUMERIC(12, 2) NOT NULL DEFAULT 0.0,
            referencia      VARCHAR(80)        NULL,
            endereco        VARCHAR(200)       NULL,
            versao          INTEGER        NOT NULL DEFAULT 1,
            criado_em       TIMESTAMPTZ    NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_em   TIMESTAMPTZ    NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT uq_usuario_codigo UNIQUE (usuario_id, codigo)
        );

        CREATE TABLE IF NOT EXISTS movimentacoes (
            id                   BIGSERIAL      PRIMARY KEY,
            produto_id           BIGINT         NOT NULL REFERENCES produtos (id) ON DELETE CASCADE ON UPDATE CASCADE,
            usuario_id           BIGINT         NOT NULL REFERENCES usuarios (id) ON DELETE RESTRICT ON UPDATE CASCADE,
            organization_id      BIGINT             NULL REFERENCES organizations (id) ON DELETE CASCADE ON UPDATE CASCADE,
            tipo                 VARCHAR(10)    NOT NULL CHECK (tipo IN ('entrada', 'saida')),
            quantidade           INTEGER        NOT NULL CHECK (quantidade > 0),
            custo_unitario       NUMERIC(12, 2) NOT NULL DEFAULT 0.0,
            documento_referencia VARCHAR(100)       NULL,
            motivo               VARCHAR(255)       NULL,
            criado_em            TIMESTAMPTZ    NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS audit_logs (
            id              BIGSERIAL   PRIMARY KEY,
            organization_id BIGINT          NULL REFERENCES organizations (id) ON DELETE SET NULL ON UPDATE CASCADE,
            usuario_id      BIGINT      NOT NULL REFERENCES usuarios (id) ON DELETE CASCADE ON UPDATE CASCADE,
            acao            VARCHAR(80) NOT NULL,
            detalhes        TEXT            NULL,
            ip_address      VARCHAR(50)     NULL,
            impersonated_by BIGINT          NULL REFERENCES usuarios (id) ON DELETE SET NULL ON UPDATE CASCADE,
            criado_em       TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS suporte_chamados (
            id              BIGSERIAL    PRIMARY KEY,
            usuario_id      BIGINT       NOT NULL REFERENCES usuarios (id) ON DELETE CASCADE ON UPDATE CASCADE,
            organization_id BIGINT           NULL REFERENCES organizations (id) ON DELETE SET NULL ON UPDATE CASCADE,
            tipo            VARCHAR(80)  NOT NULL DEFAULT 'duvida',
            mensagem        TEXT         NOT NULL,
            destinatario    VARCHAR(150) NOT NULL DEFAULT 'w.thiagosan@gmail.com',
            status          VARCHAR(30)  NOT NULL DEFAULT 'aberto',
            criado_em       TIMESTAMPTZ  NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_produtos_usuario ON produtos (usuario_id);
        CREATE INDEX IF NOT EXISTS idx_produtos_codigo ON produtos (usuario_id, codigo);
        CREATE INDEX IF NOT EXISTS idx_produtos_org ON produtos (organization_id);
        CREATE INDEX IF NOT EXISTS idx_movimentacoes_produto ON movimentacoes (produto_id);
        CREATE INDEX IF NOT EXISTS idx_movimentacoes_usuario ON movimentacoes (usuario_id);
        CREATE INDEX IF NOT EXISTS idx_movimentacoes_org ON movimentacoes (organization_id);
        CREATE INDEX IF NOT EXISTS idx_movimentacoes_criado_em ON movimentacoes (criado_em);
        CREATE INDEX IF NOT EXISTS idx_user_org_usuario ON user_organizations (usuario_id);
        CREATE INDEX IF NOT EXISTS idx_user_org_org ON user_organizations (organization_id);
        CREATE INDEX IF NOT EXISTS idx_audit_logs_org ON audit_logs (organization_id);
        CREATE INDEX IF NOT EXISTS idx_audit_logs_usuario ON audit_logs (usuario_id);
        CREATE INDEX IF NOT EXISTS idx_audit_logs_criado_em ON audit_logs (criado_em);
        CREATE INDEX IF NOT EXISTS idx_suporte_chamados_org ON suporte_chamados (organization_id);
        CREATE INDEX IF NOT EXISTS idx_suporte_chamados_user ON suporte_chamados (usuario_id);
    ''')

    # Seed Admin e Organização Matriz Padrão
    cursor.execute("SELECT id FROM usuarios WHERE id = 1 OR email = %s", (Config.ADMIN_EMAIL,))
    admin_row = cursor.fetchone()
    if not admin_row:
        hashed_pwd = generate_password_hash(Config.ADMIN_DEFAULT_PASSWORD)
        cursor.execute(
            "INSERT INTO usuarios (id, nome, email, senha, is_admin, is_superadmin) VALUES (1, %s, %s, %s, TRUE, TRUE)",
            (Config.ADMIN_NAME, Config.ADMIN_EMAIL, hashed_pwd)
        )
    else:
        cursor.execute("UPDATE usuarios SET is_superadmin = TRUE, is_admin = TRUE WHERE id = %s", (admin_row['id'],))

    cursor.execute("SELECT id FROM organizations WHERE id = 1")
    if not cursor.fetchone():
        cursor.execute(
            '''INSERT INTO organizations (id, nome, slug, cnpj_ou_documento, plano, ativo)
               VALUES (1, 'SimpStock Matriz', 'matriz', '00.000.000/0001-00', 'enterprise', TRUE)'''
        )

    cursor.execute("SELECT id FROM user_organizations WHERE usuario_id = 1 AND organization_id = 1")
    if not cursor.fetchone():
        cursor.execute(
            '''INSERT INTO user_organizations (usuario_id, organization_id, role, ativo)
               VALUES (1, 1, 'superadmin', TRUE)'''
        )

    cursor.close()
    conn.close()


def _init_sqlite_db(target_db):
    """Inicializa tabelas e seeds no SQLite local para desenvolvimento e testes."""
    db = sqlite3.connect(target_db, timeout=30.0, isolation_level=None)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    db.execute("PRAGMA busy_timeout = 30000")
    try:
        db.execute("PRAGMA journal_mode = WAL")
    except Exception:
        pass

    db.executescript('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id        INTEGER      NOT NULL,
            nome      VARCHAR(100) NOT NULL,
            email     VARCHAR(150) NOT NULL UNIQUE,
            senha     VARCHAR(255) NOT NULL,
            is_admin  BOOLEAN      NOT NULL DEFAULT 0,
            criado_em TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT pk_usuarios PRIMARY KEY (id AUTOINCREMENT)
        );

        CREATE TABLE IF NOT EXISTS produtos (
            id            INTEGER      NOT NULL,
            usuario_id    INTEGER      NOT NULL,
            nome          VARCHAR(150) NOT NULL,
            marca         VARCHAR(100) NOT NULL,
            validade      DATE             NULL,
            codigo        VARCHAR(80)  NOT NULL,
            quantidade    INTEGER      NOT NULL DEFAULT 0 CHECK (quantidade >= 0),
            referencia    VARCHAR(80)      NULL,
            endereco      VARCHAR(200)     NULL,
            versao        INTEGER      NOT NULL DEFAULT 1,
            criado_em     TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT pk_produtos     PRIMARY KEY (id AUTOINCREMENT),
            CONSTRAINT uq_usuario_codigo UNIQUE (usuario_id, codigo),
            CONSTRAINT fk_prod_usuario FOREIGN KEY (usuario_id)
                REFERENCES usuarios (id) ON DELETE RESTRICT ON UPDATE CASCADE
        );

        CREATE TABLE IF NOT EXISTS movimentacoes (
            id         INTEGER      NOT NULL,
            produto_id INTEGER      NOT NULL,
            usuario_id INTEGER      NOT NULL,
            tipo       VARCHAR(10)  NOT NULL CHECK (tipo IN ('entrada', 'saida')),
            quantidade INTEGER      NOT NULL CHECK (quantidade > 0),
            motivo     VARCHAR(255)     NULL,
            criado_em  TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT pk_movimentacoes PRIMARY KEY (id AUTOINCREMENT),
            CONSTRAINT fk_mov_produto   FOREIGN KEY (produto_id)
                REFERENCES produtos (id) ON DELETE CASCADE ON UPDATE CASCADE,
            CONSTRAINT fk_mov_usuario   FOREIGN KEY (usuario_id)
                REFERENCES usuarios (id) ON DELETE RESTRICT ON UPDATE CASCADE
        );

        CREATE TABLE IF NOT EXISTS organizations (
            id                 INTEGER      NOT NULL,
            nome               VARCHAR(150) NOT NULL,
            slug               VARCHAR(80)  NOT NULL UNIQUE,
            cnpj_ou_documento  VARCHAR(30)      NULL,
            plano              VARCHAR(50)  NOT NULL DEFAULT 'enterprise',
            ativo              BOOLEAN      NOT NULL DEFAULT 1,
            criado_em          TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT pk_organizations PRIMARY KEY (id AUTOINCREMENT)
        );

        CREATE TABLE IF NOT EXISTS user_organizations (
            id              INTEGER      NOT NULL,
            usuario_id      INTEGER      NOT NULL,
            organization_id INTEGER      NOT NULL,
            role            VARCHAR(50)  NOT NULL DEFAULT 'org_operator' CHECK (role IN ('superadmin', 'org_admin', 'org_operator', 'viewer')),
            ativo           BOOLEAN      NOT NULL DEFAULT 1,
            criado_em       TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT pk_user_org PRIMARY KEY (id AUTOINCREMENT),
            CONSTRAINT uq_user_org UNIQUE (usuario_id, organization_id),
            CONSTRAINT fk_uo_usuario FOREIGN KEY (usuario_id)
                REFERENCES usuarios (id) ON DELETE CASCADE ON UPDATE CASCADE,
            CONSTRAINT fk_uo_org FOREIGN KEY (organization_id)
                REFERENCES organizations (id) ON DELETE CASCADE ON UPDATE CASCADE
        );

        CREATE TABLE IF NOT EXISTS categories (
            id              INTEGER      NOT NULL,
            organization_id INTEGER      NOT NULL,
            nome            VARCHAR(100) NOT NULL,
            descricao       VARCHAR(255)     NULL,
            criado_em       TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT pk_categories PRIMARY KEY (id AUTOINCREMENT),
            CONSTRAINT uq_cat_org_nome UNIQUE (organization_id, nome),
            CONSTRAINT fk_cat_org FOREIGN KEY (organization_id)
                REFERENCES organizations (id) ON DELETE CASCADE ON UPDATE CASCADE
        );

        CREATE TABLE IF NOT EXISTS suppliers (
            id              INTEGER      NOT NULL,
            organization_id INTEGER      NOT NULL,
            nome            VARCHAR(150) NOT NULL,
            contato         VARCHAR(100)     NULL,
            email           VARCHAR(150)     NULL,
            telefone        VARCHAR(50)      NULL,
            criado_em       TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT pk_suppliers PRIMARY KEY (id AUTOINCREMENT),
            CONSTRAINT fk_sup_org FOREIGN KEY (organization_id)
                REFERENCES organizations (id) ON DELETE CASCADE ON UPDATE CASCADE
        );

        CREATE TABLE IF NOT EXISTS audit_logs (
            id              INTEGER      NOT NULL,
            organization_id INTEGER          NULL,
            usuario_id      INTEGER      NOT NULL,
            acao            VARCHAR(80)  NOT NULL,
            detalhes        TEXT             NULL,
            ip_address      VARCHAR(50)      NULL,
            impersonated_by INTEGER          NULL,
            criado_em       TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT pk_audit_logs PRIMARY KEY (id AUTOINCREMENT),
            CONSTRAINT fk_audit_org FOREIGN KEY (organization_id)
                REFERENCES organizations (id) ON DELETE SET NULL ON UPDATE CASCADE,
            CONSTRAINT fk_audit_user FOREIGN KEY (usuario_id)
                REFERENCES usuarios (id) ON DELETE CASCADE ON UPDATE CASCADE,
            CONSTRAINT fk_audit_impersonator FOREIGN KEY (impersonated_by)
                REFERENCES usuarios (id) ON DELETE SET NULL ON UPDATE CASCADE
        );

        CREATE TABLE IF NOT EXISTS suporte_chamados (
            id              INTEGER      NOT NULL,
            usuario_id      INTEGER      NOT NULL,
            organization_id INTEGER          NULL,
            tipo            VARCHAR(80)  NOT NULL DEFAULT 'duvida',
            mensagem        TEXT         NOT NULL,
            destinatario    VARCHAR(150) NOT NULL DEFAULT 'w.thiagosan@gmail.com',
            status          VARCHAR(30)  NOT NULL DEFAULT 'aberto',
            criado_em       TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT pk_suporte_chamados PRIMARY KEY (id AUTOINCREMENT),
            CONSTRAINT fk_sup_cham_user FOREIGN KEY (usuario_id)
                REFERENCES usuarios (id) ON DELETE CASCADE ON UPDATE CASCADE,
            CONSTRAINT fk_sup_cham_org FOREIGN KEY (organization_id)
                REFERENCES organizations (id) ON DELETE SET NULL ON UPDATE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_produtos_usuario ON produtos (usuario_id);
        CREATE INDEX IF NOT EXISTS idx_produtos_codigo ON produtos (usuario_id, codigo);
        CREATE INDEX IF NOT EXISTS idx_movimentacoes_produto ON movimentacoes (produto_id);
        CREATE INDEX IF NOT EXISTS idx_movimentacoes_usuario ON movimentacoes (usuario_id);
        CREATE INDEX IF NOT EXISTS idx_movimentacoes_criado_em ON movimentacoes (criado_em);
        CREATE INDEX IF NOT EXISTS idx_suporte_chamados_org ON suporte_chamados (organization_id);
        CREATE INDEX IF NOT EXISTS idx_suporte_chamados_user ON suporte_chamados (usuario_id);
    ''')

    # Migrações idempotentes de colunas em SQLite
    _add_column_if_not_exists(db, 'usuarios', 'is_superadmin BOOLEAN NOT NULL DEFAULT 0')
    _add_column_if_not_exists(db, 'produtos', 'organization_id INTEGER NULL')
    _add_column_if_not_exists(db, 'produtos', 'categoria_id INTEGER NULL')
    _add_column_if_not_exists(db, 'produtos', 'fornecedor_id INTEGER NULL')
    _add_column_if_not_exists(db, 'produtos', 'estoque_minimo INTEGER NOT NULL DEFAULT 5')
    _add_column_if_not_exists(db, 'produtos', 'custo_unitario REAL NOT NULL DEFAULT 0.0')
    _add_column_if_not_exists(db, 'produtos', 'preco_venda REAL NOT NULL DEFAULT 0.0')
    _add_column_if_not_exists(db, 'movimentacoes', 'organization_id INTEGER NULL')
    _add_column_if_not_exists(db, 'movimentacoes', 'custo_unitario REAL NOT NULL DEFAULT 0.0')
    _add_column_if_not_exists(db, 'movimentacoes', 'documento_referencia VARCHAR(100) NULL')
    _add_column_if_not_exists(db, 'suporte_chamados', "destinatario VARCHAR(150) NOT NULL DEFAULT 'w.thiagosan@gmail.com'")

    db.executescript('''
        CREATE INDEX IF NOT EXISTS idx_produtos_org ON produtos (organization_id);
        CREATE INDEX IF NOT EXISTS idx_movimentacoes_org ON movimentacoes (organization_id);
        CREATE INDEX IF NOT EXISTS idx_user_org_usuario ON user_organizations (usuario_id);
        CREATE INDEX IF NOT EXISTS idx_user_org_org ON user_organizations (organization_id);
        CREATE INDEX IF NOT EXISTS idx_audit_logs_org ON audit_logs (organization_id);
        CREATE INDEX IF NOT EXISTS idx_audit_logs_usuario ON audit_logs (usuario_id);
        CREATE INDEX IF NOT EXISTS idx_audit_logs_criado_em ON audit_logs (criado_em);
    ''')

    # Valida ou insere administrador padrão
    admin_row = db.execute(
        "SELECT id, senha FROM usuarios WHERE id = 1 OR email = ?",
        (Config.ADMIN_EMAIL,)
    ).fetchone()

    if not admin_row:
        hashed_pwd = generate_password_hash(Config.ADMIN_DEFAULT_PASSWORD)
        db.execute(
            "INSERT INTO usuarios (id, nome, email, senha, is_admin, is_superadmin) VALUES (1, ?, ?, ?, 1, 1)",
            (Config.ADMIN_NAME, Config.ADMIN_EMAIL, hashed_pwd)
        )
    else:
        db.execute("UPDATE usuarios SET is_superadmin = 1, is_admin = 1 WHERE id = ?", (admin_row['id'],))
        senha_atual = admin_row['senha']
        if not senha_atual.startswith(('scrypt:', 'pbkdf2:')):
            novo_hash = generate_password_hash(senha_atual)
            db.execute("UPDATE usuarios SET senha = ? WHERE id = ?", (novo_hash, admin_row['id']))

    # Provisão da Organização Matriz padrão (Tenant 1)
    org_row = db.execute("SELECT id FROM organizations WHERE id = 1").fetchone()
    if not org_row:
        db.execute(
            '''INSERT INTO organizations (id, nome, slug, cnpj_ou_documento, plano, ativo)
               VALUES (1, 'SimpStock Matriz', 'matriz', '00.000.000/0001-00', 'enterprise', 1)'''
        )

    # Vincula administrador principal como superadmin e org_admin do Tenant 1
    user_org = db.execute(
        "SELECT id FROM user_organizations WHERE usuario_id = 1 AND organization_id = 1"
    ).fetchone()
    if not user_org:
        db.execute(
            '''INSERT INTO user_organizations (usuario_id, organization_id, role, ativo)
               VALUES (1, 1, 'superadmin', 1)'''
        )

    # Backfill para garantir que produtos e movimentações legadas pertençam à organização 1
    db.execute("UPDATE produtos SET organization_id = 1 WHERE organization_id IS NULL")
    db.execute("UPDATE movimentacoes SET organization_id = 1 WHERE organization_id IS NULL")

    db.commit()
    db.close()


def _add_column_if_not_exists(db, table_name: str, column_def: str):
    """Adiciona coluna de forma idempotente em tabelas SQLite sem recriação destrutiva."""
    col_name = column_def.split()[0]
    cursor = db.execute(f"PRAGMA table_info({table_name})")
    colunas_existentes = [row[1] for row in cursor.fetchall()]
    if col_name not in colunas_existentes:
        try:
            db.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_def}")
        except Exception:
            pass


def log_audit_event(db, usuario_id: int, acao: str, detalhes: str = None,
                    organization_id: int = None, impersonated_by: int = None, ip_address: str = None):
    """Registra evento rastreável e imutável no log de auditoria corporativo."""
    try:
        db.execute(
            '''INSERT INTO audit_logs (organization_id, usuario_id, acao, detalhes, ip_address, impersonated_by)
               VALUES (?, ?, ?, ?, ?, ?)''',
            (organization_id, usuario_id, acao, detalhes, ip_address, impersonated_by)
        )
    except Exception:
        pass


def row_to_dict(row):
    return dict(row) if row else None


def rows_to_list(rows):
    return [dict(r) for r in rows]
