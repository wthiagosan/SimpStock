import re
import sqlite3
from flask import request, jsonify, g
from . import superadmin_bp
from database import get_db, row_to_dict, rows_to_list, log_audit_event
from auth import superadmin_required, generate_token


def _slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r'[\s_]+', '-', text)
    text = re.sub(r'[^\w\-]', '', text)
    return text.strip('-') or 'org'


@superadmin_bp.route('/superadmin/overview', methods=['GET'])
@superadmin_required
def get_overview():
    """Retorna métricas consolidadas da plataforma e logs de auditoria recentes."""
    db = get_db()

    total_orgs = db.execute("SELECT COUNT(*) AS total FROM organizations").fetchone()['total']
    active_orgs = db.execute("SELECT COUNT(*) AS total FROM organizations WHERE ativo = 1").fetchone()['total']
    total_users = db.execute("SELECT COUNT(*) AS total FROM usuarios").fetchone()['total']
    total_products = db.execute("SELECT COUNT(*) AS total FROM produtos").fetchone()['total']
    
    val_row = db.execute("SELECT COALESCE(SUM(quantidade * custo_unitario), 0) AS total_val, COALESCE(SUM(quantidade), 0) AS total_itens FROM produtos").fetchone()
    total_inventory_value = round(float(val_row['total_val']), 2)
    total_inventory_items = int(val_row['total_itens'])

    recent_audits = db.execute(
        '''SELECT a.id, a.acao, a.detalhes, a.ip_address, a.impersonated_by, a.criado_em,
                  u.nome AS usuario_nome, u.email AS usuario_email,
                  o.nome AS organization_nome
           FROM audit_logs a
           JOIN usuarios u ON u.id = a.usuario_id
           LEFT JOIN organizations o ON o.id = a.organization_id
           ORDER BY a.criado_em DESC LIMIT 15'''
    ).fetchall()

    return jsonify({
        'status': 'success',
        'overview': {
            'total_organizations': total_orgs,
            'active_organizations': active_orgs,
            'total_users': total_users,
            'total_products': total_products,
            'total_inventory_value': total_inventory_value,
            'total_inventory_items': total_inventory_items,
            'recent_audits': rows_to_list(recent_audits)
        }
    }), 200


@superadmin_bp.route('/superadmin/organizations', methods=['GET'])
@superadmin_required
def list_organizations():
    """Lista todas as organizações da plataforma com contadores e valoração agregada."""
    db = get_db()
    rows = db.execute(
        '''SELECT o.id, o.nome, o.slug, o.cnpj_ou_documento, o.plano, o.ativo, o.criado_em,
                  (SELECT COUNT(*) FROM user_organizations WHERE organization_id = o.id AND ativo = 1) AS total_usuarios,
                  (SELECT COUNT(*) FROM produtos WHERE organization_id = o.id) AS total_produtos,
                  (SELECT COALESCE(SUM(quantidade * custo_unitario), 0) FROM produtos WHERE organization_id = o.id) AS valor_estoque
           FROM organizations o
           ORDER BY o.id ASC'''
    ).fetchall()

    orgs = []
    for r in rows:
        d = dict(r)
        d['ativo'] = bool(d['ativo'])
        d['valor_estoque'] = round(float(d['valor_estoque']), 2)
        orgs.append(d)

    return jsonify(orgs), 200


@superadmin_bp.route('/superadmin/organizations', methods=['POST'])
@superadmin_required
def create_organization():
    """Provisiona um novo tenant (empresa) na plataforma."""
    data = request.get_json() or {}
    nome = (data.get('nome') or '').strip()
    cnpj = (data.get('cnpj_ou_documento') or '').strip() or None
    plano = (data.get('plano') or 'enterprise').strip().lower()
    raw_slug = (data.get('slug') or '').strip()

    if not nome:
        return jsonify({'message': 'O nome da organização é obrigatório.'}), 400

    slug = _slugify(raw_slug if raw_slug else nome)

    db = get_db()
    try:
        cursor = db.execute(
            '''INSERT INTO organizations (nome, slug, cnpj_ou_documento, plano, ativo)
               VALUES (?, ?, ?, ?, 1)''',
            (nome, slug, cnpj, plano)
        )
        new_org_id = cursor.lastrowid

        # Se informado um administrador para a organização
        admin_email = (data.get('admin_email') or '').strip().lower()
        if admin_email:
            user = db.execute("SELECT id FROM usuarios WHERE lower(email) = ?", (admin_email,)).fetchone()
            if user:
                db.execute(
                    '''INSERT OR IGNORE INTO user_organizations (usuario_id, organization_id, role, ativo)
                       VALUES (?, ?, 'org_admin', 1)''',
                    (user['id'], new_org_id)
                )

        log_audit_event(
            db, g.user['id'], 'superadmin.organization_created',
            f"Organização '{nome}' (slug: {slug}) criada com plano {plano}.",
            organization_id=new_org_id, ip_address=request.remote_addr
        )
        db.commit()

        created_org = row_to_dict(db.execute(
            'SELECT * FROM organizations WHERE id = ?', (new_org_id,)
        ).fetchone())

        return jsonify({
            'message': f"Organização '{nome}' provisionada com sucesso!",
            'organization': created_org
        }), 201

    except sqlite3.IntegrityError:
        db.rollback()
        return jsonify({'message': f"Já existe uma organização com o identificador/slug '{slug}'."}), 409


@superadmin_bp.route('/superadmin/organizations/<int:org_id>', methods=['PUT'])
@superadmin_required
def update_organization(org_id):
    """Atualiza configurações cadastrais, plano e status da empresa."""
    data = request.get_json() or {}
    db = get_db()

    org = row_to_dict(db.execute('SELECT * FROM organizations WHERE id = ?', (org_id,)).fetchone())
    if not org:
        return jsonify({'message': 'Organização não encontrada.'}), 404

    nome = data.get('nome', org['nome']).strip()
    plano = data.get('plano', org['plano']).strip().lower()
    cnpj = data.get('cnpj_ou_documento', org['cnpj_ou_documento'])
    ativo = 1 if data.get('ativo', org['ativo']) else 0

    db.execute(
        '''UPDATE organizations
           SET nome = ?, plano = ?, cnpj_ou_documento = ?, ativo = ?
           WHERE id = ?''',
        (nome, plano, cnpj, ativo, org_id)
    )
    log_audit_event(
        db, g.user['id'], 'superadmin.organization_updated',
        f"Organização #{org_id} atualizada (Nome: {nome}, Plano: {plano}, Ativo: {ativo})",
        organization_id=org_id, ip_address=request.remote_addr
    )
    db.commit()

    updated = row_to_dict(db.execute('SELECT * FROM organizations WHERE id = ?', (org_id,)).fetchone())
    return jsonify({'message': 'Organização atualizada com sucesso!', 'organization': updated}), 200


@superadmin_bp.route('/superadmin/impersonate', methods=['POST'])
@superadmin_required
def impersonate():
    """Permite ao Superadmin assumir o contexto de qualquer organização com auditoria estrita."""
    data = request.get_json() or {}
    target_org_id = data.get('target_org_id')
    reason = (data.get('reason') or '').strip()

    if not target_org_id:
        return jsonify({'message': 'O ID da organização alvo (target_org_id) é obrigatório.'}), 400

    if not reason or len(reason) < 5:
        return jsonify({
            'message': 'Justificativa de auditoria é obrigatória para impersonação técnica (mínimo 5 caracteres).'
        }), 400

    db = get_db()
    org = row_to_dict(db.execute(
        'SELECT * FROM organizations WHERE id = ?', (target_org_id,)
    ).fetchone())

    if not org:
        return jsonify({'message': 'Organização de destino não encontrada.'}), 404

    if not org['ativo']:
        return jsonify({'message': 'Não é possível impersonar uma organização desativada.'}), 403

    # Busca usuário admin da organização ou usa o próprio superadmin atuando como org_admin
    target_user_id = data.get('target_user_id')
    if target_user_id:
        target_user = row_to_dict(db.execute(
            'SELECT id, nome, email, is_admin FROM usuarios WHERE id = ?', (target_user_id,)
        ).fetchone())
        if not target_user:
            return jsonify({'message': 'Usuário alvo não encontrado.'}), 404
    else:
        target_user = g.user

    # Emite token de suporte restrito (válido por 1 hora) com marca de impersonação
    impersonation_token = generate_token(
        user_id=target_user['id'],
        nome=target_user['nome'],
        email=target_user['email'],
        is_admin=True,
        is_superadmin=True,
        org_id=org['id'],
        org_role='org_admin',
        impersonated_by=g.user['id'],
        expires_hours=1.0
    )

    # Registro criptográfico no log de auditoria
    log_audit_event(
        db,
        usuario_id=target_user['id'],
        acao='superadmin.impersonate_start',
        detalhes=f"Superadmin #{g.user['id']} ({g.user['email']}) iniciou impersonação na Org #{org['id']} ({org['nome']}). Motivo: {reason}",
        organization_id=org['id'],
        impersonated_by=g.user['id'],
        ip_address=request.remote_addr
    )
    db.commit()

    return jsonify({
        'message': f"Sessão de suporte iniciada na organização '{org['nome']}'.",
        'token': impersonation_token,
        'organization': org,
        'target_user': {
            'id': target_user['id'],
            'nome': target_user['nome'],
            'email': target_user['email']
        },
        'impersonated_by': {
            'id': g.user['id'],
            'email': g.user['email'],
            'nome': g.user['nome']
        },
        'reason': reason
    }), 200


@superadmin_bp.route('/superadmin/audit-logs', methods=['GET'])
@superadmin_required
def list_audit_logs():
    """Consulta histórico completo de auditoria do sistema."""
    db = get_db()
    org_id = request.args.get('organization_id', type=int)
    limit = min(request.args.get('limit', default=50, type=int), 200)

    query = '''
        SELECT a.id, a.acao, a.detalhes, a.ip_address, a.impersonated_by, a.criado_em,
               u.nome AS usuario_nome, u.email AS usuario_email,
               o.nome AS organization_nome,
               imp.nome AS impersonator_nome
        FROM audit_logs a
        JOIN usuarios u ON u.id = a.usuario_id
        LEFT JOIN organizations o ON o.id = a.organization_id
        LEFT JOIN usuarios imp ON imp.id = a.impersonated_by
    '''
    params = []
    if org_id:
        query += ' WHERE a.organization_id = ?'
        params.append(org_id)

    query += ' ORDER BY a.criado_em DESC LIMIT ?'
    params.append(limit)

    rows = db.execute(query, params).fetchall()
    return jsonify(rows_to_list(rows)), 200
