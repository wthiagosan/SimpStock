import sqlite3
from flask import request, jsonify, g
from . import produtos_bp
from database import get_db, row_to_dict, rows_to_list, log_audit_event
from auth import token_required


@produtos_bp.route('/produtos', methods=['GET'])
@token_required
def get_produtos():
    """Lista produtos respeitando rigorosamente o isolamento multi-tenant da organização ativa."""
    db = get_db()
    is_super = bool(g.user.get('is_superadmin'))
    is_admin = bool(g.user.get('is_admin'))
    org_id = getattr(g, 'org_id', None)
    filter_user_id = request.args.get('usuario_id', type=int)

    base_query = '''
        SELECT p.*,
               c.nome AS categoria_nome,
               s.nome AS fornecedor_nome
        FROM produtos p
        LEFT JOIN categories c ON c.id = p.categoria_id
        LEFT JOIN suppliers s ON s.id = p.fornecedor_id
    '''
    conditions = []
    params = []

    # Superadmin global sem filtro explícito de tenant vê tudo (caso não esteja restrito a uma org)
    if is_super and not request.headers.get('X-Organization-Id') and not request.args.get('organization_id') and not getattr(g, 'impersonated_by', None):
        if filter_user_id:
            conditions.append('p.usuario_id = ?')
            params.append(filter_user_id)
    else:
        # Isolamento Multi-Tenant: restringe à organização ativa (com fallback para usuario_id se produto sem org)
        if org_id:
            if is_admin or getattr(g, 'org_role', '') in ('superadmin', 'org_admin'):
                if filter_user_id:
                    conditions.append('(p.organization_id = ? OR (p.organization_id IS NULL AND p.usuario_id = ?)) AND p.usuario_id = ?')
                    params.extend([org_id, g.user['id'], filter_user_id])
                else:
                    conditions.append('(p.organization_id = ? OR (p.organization_id IS NULL AND p.usuario_id = ?))')
                    params.extend([org_id, g.user['id']])
            else:
                # Operador/Lojista comum vê estritamente seus próprios produtos dentro da organização
                conditions.append('p.usuario_id = ? AND (p.organization_id = ? OR p.organization_id IS NULL)')
                params.extend([g.user['id'], org_id])
        else:
            if not is_admin:
                conditions.append('p.usuario_id = ?')
                params.append(g.user['id'])
            elif filter_user_id:
                conditions.append('p.usuario_id = ?')
                params.append(filter_user_id)

    if conditions:
        base_query += ' WHERE ' + ' AND '.join(conditions)

    base_query += ' ORDER BY p.id ASC'

    rows = db.execute(base_query, params).fetchall()
    produtos = rows_to_list(rows)

    # Enriquece cada item com cálculos financeiros em tempo real
    for p in produtos:
        custo = float(p.get('custo_unitario') or 0.0)
        qtd = int(p.get('quantidade') or 0)
        minimo = int(p.get('estoque_minimo') or 5)
        p['valor_total'] = round(qtd * custo, 2)
        p['status_estoque'] = 'ruptura' if qtd == 0 else ('critico' if qtd <= minimo else 'saudavel')

    return jsonify(produtos), 200


@produtos_bp.route('/produtos', methods=['POST'])
@token_required
def add_produto():
    """Cadastra novo produto associado à organização ativa e gera movimentação inicial rastreável."""
    data = request.get_json() or {}
    nome = (data.get('nome') or '').strip()
    marca = (data.get('marca') or '').strip()
    codigo = (data.get('codigo') or '').strip()
    referencia = (data.get('referencia') or '').strip() or None
    validade = data.get('validade') or None
    endereco = (data.get('endereco') or '').strip() or None

    try:
        quantidade = int(data.get('quantidade', 0))
    except (ValueError, TypeError):
        return jsonify({'message': 'A quantidade deve ser um número inteiro válido.'}), 400

    if quantidade < 0:
        return jsonify({'message': 'A quantidade não pode ser negativa.'}), 400

    if not nome or not marca or not codigo:
        return jsonify({'message': 'Nome, marca e código (SKU) são obrigatórios.'}), 400

    try:
        estoque_minimo = max(0, int(data.get('estoque_minimo', 5)))
        custo_unitario = max(0.0, float(data.get('custo_unitario', 0.0)))
        preco_venda = max(0.0, float(data.get('preco_venda', 0.0)))
    except (ValueError, TypeError):
        return jsonify({'message': 'Valores numéricos de custo, preço ou estoque mínimo inválidos.'}), 400

    categoria_id = data.get('categoria_id') or None
    fornecedor_id = data.get('fornecedor_id') or None
    org_id = getattr(g, 'org_id', 1) or 1

    # Determina o dono do produto: admin pode especificar usuario_id; usuário comum sempre grava no próprio ID
    if g.user.get('is_admin') and data.get('usuario_id'):
        target_user_id = int(data.get('usuario_id'))
    else:
        target_user_id = g.user['id']

    db = get_db()
    try:
        db.execute("BEGIN IMMEDIATE")
        cursor = db.execute(
            '''INSERT INTO produtos
               (organization_id, usuario_id, nome, marca, validade, codigo,
                quantidade, referencia, endereco, estoque_minimo, custo_unitario, preco_venda,
                categoria_id, fornecedor_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (org_id, target_user_id, nome, marca, validade, codigo,
             quantidade, referencia, endereco, estoque_minimo, custo_unitario, preco_venda,
             categoria_id, fornecedor_id)
        )
        novo_id = cursor.lastrowid

        if quantidade > 0:
            db.execute(
                '''INSERT INTO movimentacoes (organization_id, produto_id, usuario_id, tipo, quantidade, motivo, custo_unitario)
                   VALUES (?, ?, ?, 'entrada', ?, 'Cadastro inicial', ?)''',
                (org_id, novo_id, g.user['id'], quantidade, custo_unitario)
            )

        log_audit_event(
            db, g.user['id'], 'product.create',
            f"Produto SKU '{codigo}' ({nome}) cadastrado com estoque inicial de {quantidade}.",
            organization_id=org_id, impersonated_by=getattr(g, 'impersonated_by', None),
            ip_address=request.remote_addr
        )

        db.commit()
        produto = row_to_dict(db.execute(
            'SELECT * FROM produtos WHERE id = ?', (novo_id,)
        ).fetchone())

        return jsonify({'message': 'Produto cadastrado com sucesso!', 'produto': produto}), 201

    except sqlite3.IntegrityError as e:
        db.rollback()
        err_msg = str(e).lower()
        if 'unique constraint failed' in err_msg and ('codigo' in err_msg or 'produtos' in err_msg):
            return jsonify({'message': f'Já existe um produto com o código SKU \"{codigo}\".'}), 409
        return jsonify({'message': 'Erro de integridade ao processar o cadastro do produto.'}), 400
    except Exception:
        db.rollback()
        return jsonify({'message': 'Erro interno ao processar o cadastro do produto.'}), 500


@produtos_bp.route('/produtos/<int:id_produto>', methods=['PUT'])
@token_required
def update_produto(id_produto):
    """Atualização transacional de dados cadastrais e saldo de estoque com auditoria."""
    data = request.get_json() or {}
    db = get_db()

    try:
        db.execute("BEGIN IMMEDIATE")

        produto = row_to_dict(db.execute(
            'SELECT * FROM produtos WHERE id = ?', (id_produto,)
        ).fetchone())

        if not produto:
            db.rollback()
            return jsonify({'message': 'Produto não encontrado.'}), 404

        # Regra de autorização Multi-Tenant
        is_super = bool(g.user.get('is_superadmin'))
        is_admin = bool(g.user.get('is_admin'))
        prod_org = produto.get('organization_id')
        current_org = getattr(g, 'org_id', None)

        if not (is_super or is_admin):
            if prod_org and current_org and prod_org != current_org:
                db.rollback()
                return jsonify({'message': 'Sem permissão para alterar produtos de outra organização.'}), 403
            if produto['usuario_id'] != g.user['id']:
                db.rollback()
                return jsonify({'message': 'Sem permissão para alterar produtos de outro lojista.'}), 403

        quantidade_anterior = produto['quantidade']
        nova_quantidade = data.get('quantidade', quantidade_anterior)

        try:
            nova_quantidade = int(nova_quantidade)
        except (ValueError, TypeError):
            db.rollback()
            return jsonify({'message': 'A quantidade deve ser um número inteiro.'}), 400

        if nova_quantidade < 0:
            db.rollback()
            return jsonify({'message': 'A quantidade não pode ser negativa.'}), 400

        nome = data.get('nome', produto['nome'])
        marca = data.get('marca', produto['marca'])
        validade = data.get('validade', produto['validade']) or None
        codigo = data.get('codigo', produto['codigo'])
        referencia = data.get('referencia', produto['referencia'])
        endereco = data.get('endereco', produto['endereco'])

        estoque_minimo = int(data.get('estoque_minimo', produto.get('estoque_minimo', 5) or 5))
        custo_unitario = float(data.get('custo_unitario', produto.get('custo_unitario', 0.0) or 0.0))
        preco_venda = float(data.get('preco_venda', produto.get('preco_venda', 0.0) or 0.0))
        categoria_id = data.get('categoria_id', produto.get('categoria_id'))
        fornecedor_id = data.get('fornecedor_id', produto.get('fornecedor_id'))

        db.execute(
            '''UPDATE produtos
               SET nome = ?, marca = ?, validade = ?, codigo = ?,
                   quantidade = ?, referencia = ?, endereco = ?,
                   estoque_minimo = ?, custo_unitario = ?, preco_venda = ?,
                   categoria_id = ?, fornecedor_id = ?,
                   versao = versao + 1,
                   atualizado_em = CURRENT_TIMESTAMP
               WHERE id = ?''',
            (nome, marca, validade, codigo, nova_quantidade, referencia, endereco,
             estoque_minimo, custo_unitario, preco_venda, categoria_id, fornecedor_id, id_produto)
        )

        diff = nova_quantidade - quantidade_anterior
        if diff != 0:
            tipo = 'entrada' if diff > 0 else 'saida'
            motivo = data.get('motivo') or 'Atualização manual de estoque'
            db.execute(
                '''INSERT INTO movimentacoes (organization_id, produto_id, usuario_id, tipo, quantidade, motivo, custo_unitario)
                   VALUES (?, ?, ?, ?, ?, ?, ?)''',
                (prod_org or current_org or 1, id_produto, g.user['id'], tipo, abs(diff), motivo, custo_unitario)
            )

        log_audit_event(
            db, g.user['id'], 'product.update',
            f"Produto #{id_produto} SKU '{codigo}' atualizado. Qtd anterior: {quantidade_anterior}, Nova: {nova_quantidade}",
            organization_id=prod_org or current_org, impersonated_by=getattr(g, 'impersonated_by', None),
            ip_address=request.remote_addr
        )

        db.commit()
        produto_atualizado = row_to_dict(db.execute(
            'SELECT * FROM produtos WHERE id = ?', (id_produto,)
        ).fetchone())

        return jsonify({'message': 'Produto atualizado com sucesso!', 'produto': produto_atualizado}), 200

    except sqlite3.IntegrityError as e:
        db.rollback()
        err_msg = str(e).lower()
        if 'unique constraint failed' in err_msg and ('codigo' in err_msg or 'produtos' in err_msg):
            return jsonify({'message': f'Já existe um produto com o código SKU \"{codigo}\".'}), 409
        if 'check constraint failed' in err_msg:
            return jsonify({'message': 'A quantidade não pode ser negativa.'}), 400
        return jsonify({'message': 'Erro de integridade ao atualizar o produto.'}), 400
    except Exception:
        db.rollback()
        return jsonify({'message': 'Erro interno ao atualizar produto.'}), 500


@produtos_bp.route('/produtos/<int:id_produto>/movimentar', methods=['POST'])
@token_required
def movimentar_produto(id_produto):
    """Executa entrada ou saída de estoque atômica com trava imediata de concorrência e auditoria."""
    data = request.get_json() or {}
    tipo = (data.get('tipo') or '').strip().lower()
    motivo = (data.get('motivo') or '').strip() or 'Movimentação operacional'

    if tipo not in ('entrada', 'saida'):
        return jsonify({'message': "Tipo de movimentação inválido. Deve ser 'entrada' ou 'saida'."}), 400

    try:
        quantidade = int(data.get('quantidade', 0))
    except (ValueError, TypeError):
        return jsonify({'message': 'A quantidade deve ser um número inteiro válido.'}), 400

    if quantidade <= 0:
        return jsonify({'message': 'A quantidade deve ser estritamente maior que zero.'}), 400

    db = get_db()
    try:
        db.execute("BEGIN IMMEDIATE")

        produto = row_to_dict(db.execute(
            'SELECT * FROM produtos WHERE id = ?', (id_produto,)
        ).fetchone())

        if not produto:
            db.rollback()
            return jsonify({'message': 'Produto não encontrado.'}), 404

        is_super = bool(g.user.get('is_superadmin'))
        is_admin = bool(g.user.get('is_admin'))
        prod_org = produto.get('organization_id')
        current_org = getattr(g, 'org_id', None)

        if not (is_super or is_admin):
            if prod_org and current_org and prod_org != current_org:
                db.rollback()
                return jsonify({'message': 'Sem permissão para movimentar produtos de outra organização.'}), 403
            if produto['usuario_id'] != g.user['id']:
                db.rollback()
                return jsonify({'message': 'Sem permissão para movimentar produtos de outro lojista.'}), 403

        qtd_anterior = produto['quantidade']

        if tipo == 'saida':
            if qtd_anterior < quantidade:
                db.rollback()
                return jsonify({
                    'message': f'Saldo insuficiente de estoque para esta saída. Disponível: {qtd_anterior}, Solicitado: {quantidade}.',
                    'disponivel': qtd_anterior
                }), 400
            nova_qtd = qtd_anterior - quantidade
        else:
            nova_qtd = qtd_anterior + quantidade

        db.execute(
            '''UPDATE produtos
               SET quantidade = ?, versao = versao + 1, atualizado_em = CURRENT_TIMESTAMP
               WHERE id = ?''',
            (nova_qtd, id_produto)
        )

        custo = float(produto.get('custo_unitario') or 0.0)
        db.execute(
            '''INSERT INTO movimentacoes (organization_id, produto_id, usuario_id, tipo, quantidade, motivo, custo_unitario)
               VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (prod_org or current_org or 1, id_produto, g.user['id'], tipo, quantidade, motivo, custo)
        )

        log_audit_event(
            db, g.user['id'], f'stock.{tipo}',
            f"Movimentação de {tipo} ({quantidade} un.) no produto SKU '{produto['codigo']}'. Motivo: {motivo}",
            organization_id=prod_org or current_org, impersonated_by=getattr(g, 'impersonated_by', None),
            ip_address=request.remote_addr
        )

        db.commit()

        produto_atualizado = row_to_dict(db.execute(
            'SELECT * FROM produtos WHERE id = ?', (id_produto,)
        ).fetchone())

        return jsonify({
            'message': f'Movimentação de {tipo} registrada com sucesso!',
            'produto': produto_atualizado,
            'quantidade_anterior': qtd_anterior,
            'nova_quantidade': nova_qtd
        }), 200

    except sqlite3.IntegrityError:
        db.rollback()
        return jsonify({'message': 'Violação de integridade ao registrar movimentação.'}), 400
    except Exception:
        db.rollback()
        return jsonify({'message': 'Erro interno ao registrar movimentação.'}), 500


@produtos_bp.route('/produtos/<int:id_produto>', methods=['DELETE'])
@token_required
def delete_produto(id_produto):
    """Exclusão de produto com validação de escopo organizacional."""
    db = get_db()

    produto = row_to_dict(db.execute(
        'SELECT * FROM produtos WHERE id = ?', (id_produto,)
    ).fetchone())

    if not produto:
        return jsonify({'message': 'Produto não encontrado.'}), 404

    is_super = bool(g.user.get('is_superadmin'))
    is_admin = bool(g.user.get('is_admin'))
    prod_org = produto.get('organization_id')
    current_org = getattr(g, 'org_id', None)

    if not (is_super or is_admin):
        if prod_org and current_org and prod_org != current_org:
            return jsonify({'message': 'Sem permissão para excluir produtos de outra organização.'}), 403
        if produto['usuario_id'] != g.user['id']:
            return jsonify({'message': 'Sem permissão para excluir produtos de outro lojista.'}), 403

    db.execute('DELETE FROM produtos WHERE id = ?', (id_produto,))
    log_audit_event(
        db, g.user['id'], 'product.delete',
        f"Produto #{id_produto} (SKU: {produto['codigo']}) excluído.",
        organization_id=prod_org or current_org, impersonated_by=getattr(g, 'impersonated_by', None),
        ip_address=request.remote_addr
    )
    db.commit()
    return jsonify({'message': 'Produto excluído com sucesso!'}), 200


@produtos_bp.route('/produtos/kpis', methods=['GET'])
@token_required
def get_kpis():
    """Retorna métricas executivas consolidadas da organização ativa (valoração, giro e alertas)."""
    db = get_db()
    org_id = getattr(g, 'org_id', None)
    is_super = bool(g.user.get('is_superadmin'))

    query = 'SELECT * FROM produtos'
    params = []

    if not is_super or org_id:
        target_org = org_id or 1
        query += ' WHERE organization_id = ? OR (organization_id IS NULL AND usuario_id = ?)'
        params.extend([target_org, g.user['id']])

    produtos = rows_to_list(db.execute(query, params).fetchall())

    total_skus = len(produtos)
    total_itens = sum(p['quantidade'] for p in produtos)
    valor_imobilizado = round(sum(p['quantidade'] * float(p.get('custo_unitario') or 0.0) for p in produtos), 2)
    valor_venda_potencial = round(sum(p['quantidade'] * float(p.get('preco_venda') or 0.0) for p in produtos), 2)

    itens_baixo_estoque = 0
    itens_esgotados = 0
    itens_saudaveis = 0

    for p in produtos:
        qtd = p['quantidade']
        minimo = p.get('estoque_minimo') or 5
        if qtd == 0:
            itens_esgotados += 1
        elif qtd <= minimo:
            itens_baixo_estoque += 1
        else:
            itens_saudaveis += 1

    # Movimentações recentes
    mov_query = '''
        SELECT m.id, m.tipo, m.quantidade, m.motivo, m.criado_em,
               p.nome AS produto_nome, p.codigo AS produto_codigo,
               u.nome AS usuario_nome
        FROM movimentacoes m
        JOIN produtos p ON p.id = m.produto_id
        JOIN usuarios u ON u.id = m.usuario_id
    '''
    mov_params = []
    if org_id:
        mov_query += ' WHERE m.organization_id = ?'
        mov_params.append(org_id)
    mov_query += ' ORDER BY m.criado_em DESC LIMIT 10'

    recent_movements = rows_to_list(db.execute(mov_query, mov_params).fetchall())

    return jsonify({
        'total_skus': total_skus,
        'total_itens': total_itens,
        'valor_imobilizado': valor_imobilizado,
        'valor_venda_potencial': valor_venda_potencial,
        'itens_baixo_estoque': itens_baixo_estoque,
        'itens_esgotados': itens_esgotados,
        'itens_saudaveis': itens_saudaveis,
        'movimentacoes_recentes': recent_movements,
        'organization_id': org_id
    }), 200
