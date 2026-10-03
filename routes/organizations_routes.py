import sqlite3
from flask import request, jsonify, g
from . import organizations_bp
from database import get_db, row_to_dict, rows_to_list, log_audit_event
from auth import token_required, org_admin_required, generate_token


@organizations_bp.route('/organizations/my', methods=['GET'])
@token_required
def list_my_organizations():
    """Lista todas as organizações às quais o usuário logado possui acesso."""
    db = get_db()
    is_super = bool(g.user.get('is_superadmin'))

    if is_super:
        # Superadmin tem acesso a todas as empresas cadastradas
        rows = db.execute(
            '''SELECT o.id, o.nome, o.slug, o.cnpj_ou_documento, o.plano, o.ativo,
                      'superadmin' AS role
               FROM organizations o
               WHERE o.ativo = 1
               ORDER BY o.id ASC'''
        ).fetchall()
    else:
        rows = db.execute(
            '''SELECT o.id, o.nome, o.slug, o.cnpj_ou_documento, o.plano, o.ativo,
                      uo.role
               FROM user_organizations uo
               JOIN organizations o ON o.id = uo.organization_id
               WHERE uo.usuario_id = ? AND uo.ativo = 1 AND o.ativo = 1
               ORDER BY o.id ASC''',
            (g.user['id'],)
        ).fetchall()

    orgs = rows_to_list(rows)
    return jsonify({
        'organizations': orgs,
        'active_organization_id': getattr(g, 'org_id', None)
    }), 200


@organizations_bp.route('/organizations/switch', methods=['POST'])
@token_required
def switch_organization():
    """Alterna o contexto de organização ativa do usuário emitindo novo token com claims atualizadas."""
    data = request.get_json() or {}
    target_org_id = data.get('organization_id')

    if not target_org_id:
        return jsonify({'message': 'O ID da organização (organization_id) é obrigatório.'}), 400

    db = get_db()
    org = row_to_dict(db.execute(
        'SELECT * FROM organizations WHERE id = ? AND ativo = 1',
        (target_org_id,)
    ).fetchone())

    if not org:
        return jsonify({'message': 'Organização não encontrada ou inativa.'}), 404

    is_super = bool(g.user.get('is_superadmin'))
    role = 'superadmin'

    if not is_super:
        membership = row_to_dict(db.execute(
            'SELECT role FROM user_organizations WHERE usuario_id = ? AND organization_id = ? AND ativo = 1',
            (g.user['id'], target_org_id)
        ).fetchone())

        if not membership:
            return jsonify({'message': 'Acesso negado. Você não é membro desta organização.'}), 403

        role = membership['role']

    # Emite novo token com o tenant_id ativo
    new_token = generate_token(
        user_id=g.user['id'],
        nome=g.user['nome'],
        email=g.user['email'],
        is_admin=bool(g.user.get('is_admin')),
        is_superadmin=is_super,
        org_id=org['id'],
        org_role=role,
        impersonated_by=getattr(g, 'impersonated_by', None)
    )

    log_audit_event(
        db, g.user['id'], 'tenant.switch',
        f"Contexto alterado para a organização #{org['id']} ({org['nome']})",
        organization_id=org['id'], ip_address=request.remote_addr
    )
    db.commit()

    return jsonify({
        'message': f"Contexto alterado com sucesso para '{org['nome']}'.",
        'token': new_token,
        'organization': org,
        'role': role
    }), 200


@organizations_bp.route('/organizations/current', methods=['GET'])
@token_required
def get_current_organization():
    """Retorna detalhes da organização ativa no contexto da requisição atual."""
    org_id = getattr(g, 'org_id', 1)
    db = get_db()
    org = row_to_dict(db.execute(
        'SELECT id, nome, slug, cnpj_ou_documento, plano, ativo, criado_em FROM organizations WHERE id = ?',
        (org_id,)
    ).fetchone())

    if not org:
        return jsonify({'message': 'Organização ativa não encontrada.'}), 404

    return jsonify({
        'organization': org,
        'role': getattr(g, 'org_role', 'org_operator'),
        'impersonated_by': getattr(g, 'impersonated_by', None)
    }), 200


@organizations_bp.route('/organizations/current/users', methods=['GET'])
@org_admin_required
def list_organization_users():
    """Lista colaboradores e seus papéis na organização ativa."""
    org_id = getattr(g, 'org_id', 1)
    db = get_db()
    rows = db.execute(
        '''SELECT u.id, u.nome, u.email, u.is_admin, uo.role, uo.ativo, uo.criado_em
           FROM user_organizations uo
           JOIN usuarios u ON u.id = uo.usuario_id
           WHERE uo.organization_id = ?
           ORDER BY u.nome ASC''',
        (org_id,)
    ).fetchall()

    return jsonify(rows_to_list(rows)), 200


@organizations_bp.route('/organizations/current/users', methods=['POST'])
@org_admin_required
def add_organization_user():
    """Vincula ou convida um colaborador para a organização ativa."""
    data = request.get_json() or {}
    email = (data.get('email') or '').strip().lower()
    role = (data.get('role') or 'org_operator').strip().lower()

    if not email:
        return jsonify({'message': 'E-mail do colaborador é obrigatório.'}), 400

    if role not in ('org_admin', 'org_operator', 'viewer'):
        return jsonify({'message': "Papel inválido. Escolha entre 'org_admin', 'org_operator' ou 'viewer'."}), 400

    org_id = getattr(g, 'org_id', 1)
    db = get_db()

    user = row_to_dict(db.execute('SELECT id, nome, email FROM usuarios WHERE lower(email) = ?', (email,)).fetchone())
    if not user:
        return jsonify({'message': f"Usuário com e-mail '{email}' ainda não possui conta na plataforma."}), 404

    try:
        db.execute(
            '''INSERT INTO user_organizations (usuario_id, organization_id, role, ativo)
               VALUES (?, ?, ?, 1)
               ON CONFLICT(usuario_id, organization_id) DO UPDATE SET role = ?, ativo = 1''',
            (user['id'], org_id, role, role)
        )
        log_audit_event(
            db, g.user['id'], 'org.member_add',
            f"Usuário {email} vinculado à organização #{org_id} com função {role}",
            organization_id=org_id, ip_address=request.remote_addr
        )
        db.commit()

        return jsonify({
            'message': f"Colaborador {user['nome']} vinculado com sucesso como {role}!",
            'user': user,
            'role': role
        }), 201

    except Exception as e:
        db.rollback()
        return jsonify({'message': 'Erro ao vincular colaborador à organização.'}), 500


@organizations_bp.route('/organizations/current/categories', methods=['GET'])
@token_required
def list_categories():
    """Lista categorias de produtos cadastradas na organização ativa."""
    org_id = getattr(g, 'org_id', 1)
    db = get_db()
    rows = db.execute(
        'SELECT id, nome, descricao, criado_em FROM categories WHERE organization_id = ? ORDER BY nome ASC',
        (org_id,)
    ).fetchall()
    return jsonify(rows_to_list(rows)), 200


@organizations_bp.route('/organizations/current/categories', methods=['POST'])
@org_admin_required
def add_category():
    """Adiciona nova categoria de produtos na organização ativa."""
    data = request.get_json() or {}
    nome = (data.get('nome') or '').strip()
    descricao = (data.get('descricao') or '').strip() or None

    if not nome:
        return jsonify({'message': 'O nome da categoria é obrigatório.'}), 400

    org_id = getattr(g, 'org_id', 1)
    db = get_db()
    try:
        cursor = db.execute(
            'INSERT INTO categories (organization_id, nome, descricao) VALUES (?, ?, ?)',
            (org_id, nome, descricao)
        )
        db.commit()
        cat = row_to_dict(db.execute('SELECT * FROM categories WHERE id = ?', (cursor.lastrowid,)).fetchone())
        return jsonify({'message': 'Categoria cadastrada com sucesso!', 'categoria': cat}), 201
    except sqlite3.IntegrityError:
        db.rollback()
        return jsonify({'message': f"Já existe uma categoria chamada '{nome}' nesta empresa."}), 409


@organizations_bp.route('/organizations/current/suppliers', methods=['GET'])
@token_required
def list_suppliers():
    """Lista fornecedores homologados na organização ativa."""
    org_id = getattr(g, 'org_id', 1)
    db = get_db()
    rows = db.execute(
        'SELECT id, nome, contato, email, telefone, criado_em FROM suppliers WHERE organization_id = ? ORDER BY nome ASC',
        (org_id,)
    ).fetchall()
    return jsonify(rows_to_list(rows)), 200


@organizations_bp.route('/organizations/current/suppliers', methods=['POST'])
@org_admin_required
def add_supplier():
    """Cadastra novo fornecedor na organização ativa."""
    data = request.get_json() or {}
    nome = (data.get('nome') or '').strip()
    contato = (data.get('contato') or '').strip() or None
    email = (data.get('email') or '').strip() or None
    telefone = (data.get('telefone') or '').strip() or None

    if not nome:
        return jsonify({'message': 'O nome do fornecedor é obrigatório.'}), 400

    org_id = getattr(g, 'org_id', 1)
    db = get_db()
    cursor = db.execute(
        'INSERT INTO suppliers (organization_id, nome, contato, email, telefone) VALUES (?, ?, ?, ?, ?)',
        (org_id, nome, contato, email, telefone)
    )
    db.commit()
    sup = row_to_dict(db.execute('SELECT * FROM suppliers WHERE id = ?', (cursor.lastrowid,)).fetchone())
    return jsonify({'message': 'Fornecedor cadastrado com sucesso!', 'fornecedor': sup}), 201
