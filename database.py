import sqlite3
from flask import g, current_app
from werkzeug.security import generate_password_hash
from config import Config


def get_db(db_path=None):
    """Retorna ou reutiliza a conexão SQLite para o ciclo da requisição atual com modo WAL e busy timeout."""
    if db_path is None:
        try:
            target_db = current_app.config.get('DATABASE', Config.DATABASE)
        except RuntimeError:
            target_db = Config.DATABASE
    else:
        target_db = db_path

    if 'db' not in g:
        g.db = sqlite3.connect(target_db, timeout=30.0, isolation_level=None)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
        g.db.execute("PRAGMA busy_timeout = 30000")
    return g.db


def close_db(error=None):
    """Fecha a conexão com o banco ao finalizar a requisição."""
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db(db_path=None):
    """Inicializa as tabelas no SQLite com isolamento multi-tenant, índices e restrições de estoque."""
    if db_path is None:
        try:
            target_db = current_app.config.get('DATABASE', Config.DATABASE)
        except RuntimeError:
            target_db = Config.DATABASE
    else:
        target_db = db_path

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

        CREATE INDEX IF NOT EXISTS idx_produtos_usuario ON produtos (usuario_id);
        CREATE INDEX IF NOT EXISTS idx_produtos_codigo ON produtos (usuario_id, codigo);
        CREATE INDEX IF NOT EXISTS idx_movimentacoes_produto ON movimentacoes (produto_id);
        CREATE INDEX IF NOT EXISTS idx_movimentacoes_usuario ON movimentacoes (usuario_id);
        CREATE INDEX IF NOT EXISTS idx_movimentacoes_criado_em ON movimentacoes (criado_em);
    ''')

    # Migrações seguras de colunas em tabelas existentes
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

    # Índices adicionais para performance multi-tenant
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
        # Garante privilégio de superadmin para o admin padrão
        db.execute("UPDATE usuarios SET is_superadmin = 1, is_admin = 1 WHERE id = ?", (admin_row['id'],))
        # Migração transparente de senhas antigas em texto plano
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
