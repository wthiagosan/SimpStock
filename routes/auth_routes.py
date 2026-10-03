import sqlite3
from flask import request, jsonify, g
from . import auth_bp
from database import get_db, row_to_dict, log_audit_event
from auth import (
    hash_password,
    verify_password,
    is_password_valid,
    generate_token,
    token_required
)


@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    nome = (data.get('nome') or '').strip()
    email = (data.get('email') or '').strip().lower()
    senha = data.get('senha') or ''

    if not nome or not email or not senha:
        return jsonify({'message': 'Nome, email e senha são campos obrigatórios.'}), 400

    if not is_password_valid(senha):
        return jsonify({
            'message': 'Senha inválida! Use no mínimo 6 caracteres com letras e números.'
        }), 400

    db = get_db()
    try:
        hashed_pwd = hash_password(senha)
        cursor = db.execute(
            'INSERT INTO usuarios (nome, email, senha, is_admin, is_superadmin) VALUES (?, ?, ?, 0, 0)',
            (nome, email, hashed_pwd)
        )
        new_user_id = cursor.lastrowid

        # Vincula o novo usuário à organização padrão (ID 1) como operador de estoque
        db.execute(
            '''INSERT INTO user_organizations (usuario_id, organization_id, role, ativo)
               VALUES (?, 1, 'org_operator', 1)''',
            (new_user_id,)
        )
        log_audit_event(db, new_user_id, 'user.register', f'Novo usuário cadastrado: {email}', organization_id=1)
        db.commit()
        return jsonify({'message': 'Usuário criado com sucesso!'}), 201
    except sqlite3.IntegrityError:
        return jsonify({'message': 'Este endereço de e-mail já está cadastrado!'}), 400


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    email = (data.get('email') or '').strip().lower()
    senha = data.get('senha') or ''

    if not email or not senha:
        return jsonify({'message': 'E-mail e senha são obrigatórios.'}), 400

    db = get_db()
    user = row_to_dict(db.execute(
        'SELECT * FROM usuarios WHERE lower(email) = ?', (email,)
    ).fetchone())

    if user and verify_password(senha, user['senha']):
        # Migração transparente se a senha ainda estava em texto plano
        if not user['senha'].startswith(('scrypt:', 'pbkdf2:')):
            novo_hash = hash_password(senha)
            db.execute('UPDATE usuarios SET senha = ? WHERE id = ?', (novo_hash, user['id']))
            db.commit()

        is_super = bool(user.get('is_superadmin', False)) or (user['id'] == 1)

        # Busca organizações associadas ao usuário
        org_rows = db.execute(
            '''SELECT o.id, o.nome, o.slug, o.plano, uo.role
               FROM user_organizations uo
               JOIN organizations o ON o.id = uo.organization_id
               WHERE uo.usuario_id = ? AND uo.ativo = 1 AND o.ativo = 1
               ORDER BY o.id ASC''',
            (user['id'],)
        ).fetchall()

        orgs = [dict(r) for r in org_rows]

        # Se for superadmin, tem acesso a todas as organizações da plataforma
        if is_super and not orgs:
            all_orgs = db.execute('SELECT id, nome, slug, plano FROM organizations WHERE ativo = 1 ORDER BY id ASC').fetchall()
            orgs = [{'id': o['id'], 'nome': o['nome'], 'slug': o['slug'], 'plano': o['plano'], 'role': 'superadmin'} for o in all_orgs]

        # Se não houver organização vinculada, provisiona vínculo com a Matriz (Tenant 1)
        if not orgs:
            db.execute(
                "INSERT OR IGNORE INTO user_organizations (usuario_id, organization_id, role, ativo) VALUES (?, 1, 'org_operator', 1)",
                (user['id'],)
            )
            db.commit()
            orgs = [{'id': 1, 'nome': 'SimpStock Matriz', 'slug': 'matriz', 'plano': 'enterprise', 'role': 'org_operator'}]

        active_org = orgs[0]
        active_role = 'superadmin' if is_super else active_org['role']

        token = generate_token(
            user_id=user['id'],
            nome=user['nome'],
            email=user['email'],
            is_admin=bool(user['is_admin']),
            is_superadmin=is_super,
            org_id=active_org['id'],
            org_role=active_role
        )

        log_audit_event(db, user['id'], 'user.login', f'Login efetuado via {active_org["nome"]}', organization_id=active_org['id'])
        db.commit()

        return jsonify({
            'message': 'Login autorizado!',
            'token': token,
            'usuario': user['nome'],
            'usuario_id': user['id'],
            'is_admin': bool(user['is_admin']),
            'is_superadmin': is_super,
            'organizacoes': orgs,
            'organizacao_ativa': active_org
        }), 200

    return jsonify({'message': 'Email ou senha incorretos.'}), 401


@auth_bp.route('/me', methods=['GET'])
@token_required
def me():
    db = get_db()
    current_org = None
    if getattr(g, 'org_id', None):
        current_org = row_to_dict(db.execute(
            'SELECT id, nome, slug, plano, cnpj_ou_documento FROM organizations WHERE id = ?',
            (g.org_id,)
        ).fetchone())

    return jsonify({
        'usuario': g.user['nome'],
        'usuario_id': g.user['id'],
        'email': g.user['email'],
        'is_admin': bool(g.user['is_admin']),
        'is_superadmin': bool(g.user.get('is_superadmin', False)),
        'organization_id': getattr(g, 'org_id', None),
        'organization_role': getattr(g, 'org_role', 'org_operator'),
        'organization': current_org,
        'impersonated_by': getattr(g, 'impersonated_by', None)
    }), 200
