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

        CREATE INDEX IF NOT EXISTS idx_produtos_usuario ON produtos (usuario_id);
        CREATE INDEX IF NOT EXISTS idx_produtos_codigo ON produtos (usuario_id, codigo);
        CREATE INDEX IF NOT EXISTS idx_movimentacoes_produto ON movimentacoes (produto_id);
        CREATE INDEX IF NOT EXISTS idx_movimentacoes_usuario ON movimentacoes (usuario_id);
        CREATE INDEX IF NOT EXISTS idx_movimentacoes_criado_em ON movimentacoes (criado_em);
    ''')

    # Valida ou insere administrador padrão
    admin_row = db.execute(
        "SELECT id, senha FROM usuarios WHERE id = 1 OR email = ?",
        (Config.ADMIN_EMAIL,)
    ).fetchone()

    if not admin_row:
        hashed_pwd = generate_password_hash(Config.ADMIN_DEFAULT_PASSWORD)
        db.execute(
            "INSERT INTO usuarios (id, nome, email, senha, is_admin) VALUES (1, ?, ?, ?, 1)",
            (Config.ADMIN_NAME, Config.ADMIN_EMAIL, hashed_pwd)
        )
    else:
        # Migração transparente de senhas antigas em texto plano
        senha_atual = admin_row['senha']
        if not senha_atual.startswith(('scrypt:', 'pbkdf2:')):
            novo_hash = generate_password_hash(senha_atual)
            db.execute("UPDATE usuarios SET senha = ? WHERE id = ?", (novo_hash, admin_row['id']))

    db.commit()
    db.close()


def row_to_dict(row):
    return dict(row) if row else None


def rows_to_list(rows):
    return [dict(r) for r in rows]
