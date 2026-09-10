import sqlite3
from flask import request, jsonify, g
from . import produtos_bp
from database import get_db, row_to_dict, rows_to_list
from auth import token_required


@produtos_bp.route('/produtos', methods=['GET'])
@token_required
def get_produtos():
    db = get_db()
    is_admin = bool(g.user.get('is_admin'))

    # Se for admin e não solicitou filtro específico por usuario_id, lista tudo
    filter_user_id = request.args.get('usuario_id', type=int)

    if is_admin:
        if filter_user_id:
            rows = db.execute(
                'SELECT * FROM produtos WHERE usuario_id = ? ORDER BY id',
                (filter_user_id,)
            ).fetchall()
        else:
            rows = db.execute('SELECT * FROM produtos ORDER BY id').fetchall()
    else:
        # Usuários não-admin sempre veem apenas os próprios produtos (Prevenção de IDOR)
        rows = db.execute(
            'SELECT * FROM produtos WHERE usuario_id = ? ORDER BY id',
            (g.user['id'],)
        ).fetchall()

    return jsonify(rows_to_list(rows)), 200


@produtos_bp.route('/produtos', methods=['POST'])
@token_required
def add_produto():
    data = request.get_json() or {}
    nome = (data.get('nome') or '').strip()
    marca = (data.get('marca') or '').strip()
    codigo = (data.get('codigo') or '').strip()
    referencia = (data.get('referencia') or '').strip()
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

    # Determina o dono do produto: admin pode especificar usuario_id; usuário comum sempre grava no próprio ID
    if g.user.get('is_admin') and data.get('usuario_id'):
        target_user_id = int(data.get('usuario_id'))
    else:
        target_user_id = g.user['id']

    db = get_db()
    try:
        cursor = db.execute(
            '''INSERT INTO produtos
               (usuario_id, nome, marca, validade, codigo, quantidade, referencia, endereco)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
            (target_user_id, nome, marca, validade, codigo, quantidade, referencia, endereco)
        )
        novo_id = cursor.lastrowid

        if quantidade > 0:
            db.execute(
                '''INSERT INTO movimentacoes (produto_id, usuario_id, tipo, quantidade, motivo)
                   VALUES (?, ?, 'entrada', ?, 'Cadastro inicial')''',
                (novo_id, g.user['id'], quantidade)
            )

        db.commit()
        produto = row_to_dict(db.execute(
            'SELECT * FROM produtos WHERE id = ?', (novo_id,)
        ).fetchone())

        return jsonify({'message': 'Produto cadastrado com sucesso!', 'produto': produto}), 201

    except sqlite3.IntegrityError as e:
        db.rollback()
        err_msg = str(e).lower()
        if 'unique constraint failed' in err_msg and 'codigo' in err_msg:
            return jsonify({'message': f'Já existe um produto com o código SKU \"{codigo}\".'}), 409
        return jsonify({'message': f'Erro de integridade no banco de dados: {e}'}), 400


@produtos_bp.route('/produtos/<int:id_produto>', methods=['PUT'])
@token_required
def update_produto(id_produto):
    data = request.get_json() or {}
    db = get_db()

    produto = row_to_dict(db.execute(
        'SELECT * FROM produtos WHERE id = ?', (id_produto,)
    ).fetchone())

    if not produto:
        return jsonify({'message': 'Produto não encontrado.'}), 404

    # Regra de autorização: apenas admin ou dono do produto pode alterar
    if not g.user.get('is_admin') and produto['usuario_id'] != g.user['id']:
        return jsonify({'message': 'Sem permissão para alterar produtos de outro lojista.'}), 403

    quantidade_anterior = produto['quantidade']
    nova_quantidade = data.get('quantidade', quantidade_anterior)

    try:
        nova_quantidade = int(nova_quantidade)
    except (ValueError, TypeError):
        return jsonify({'message': 'A quantidade deve ser um número inteiro.'}), 400

    if nova_quantidade < 0:
        return jsonify({'message': 'A quantidade não pode ser negativa.'}), 400

    nome = data.get('nome', produto['nome'])
    marca = data.get('marca', produto['marca'])
    validade = data.get('validade', produto['validade']) or None
    codigo = data.get('codigo', produto['codigo'])
    referencia = data.get('referencia', produto['referencia'])
    endereco = data.get('endereco', produto['endereco'])

    try:
        db.execute(
            '''UPDATE produtos
               SET nome = ?, marca = ?, validade = ?, codigo = ?,
                   quantidade = ?, referencia = ?, endereco = ?,
                   atualizado_em = CURRENT_TIMESTAMP
               WHERE id = ?''',
            (nome, marca, validade, codigo, nova_quantidade, referencia, endereco, id_produto)
        )

        diff = nova_quantidade - quantidade_anterior
        if diff != 0:
            tipo = 'entrada' if diff > 0 else 'saida'
            motivo = data.get('motivo') or 'Atualização manual de estoque'
            db.execute(
                '''INSERT INTO movimentacoes (produto_id, usuario_id, tipo, quantidade, motivo)
                   VALUES (?, ?, ?, ?, ?)''',
                (id_produto, g.user['id'], tipo, abs(diff), motivo)
            )

        db.commit()
        produto_atualizado = row_to_dict(db.execute(
            'SELECT * FROM produtos WHERE id = ?', (id_produto,)
        ).fetchone())

        return jsonify({'message': 'Produto atualizado com sucesso!', 'produto': produto_atualizado}), 200

    except sqlite3.IntegrityError as e:
        db.rollback()
        return jsonify({'message': f'Erro ao atualizar produto: {e}'}), 409


@produtos_bp.route('/produtos/<int:id_produto>', methods=['DELETE'])
@token_required
def delete_produto(id_produto):
    db = get_db()

    produto = row_to_dict(db.execute(
        'SELECT * FROM produtos WHERE id = ?', (id_produto,)
    ).fetchone())

    if not produto:
        return jsonify({'message': 'Produto não encontrado.'}), 404

    # Regra de autorização: apenas admin ou dono do produto pode excluir
    if not g.user.get('is_admin') and produto['usuario_id'] != g.user['id']:
        return jsonify({'message': 'Sem permissão para excluir produtos de outro lojista.'}), 403

    db.execute('DELETE FROM produtos WHERE id = ?', (id_produto,))
    db.commit()
    return jsonify({'message': 'Produto excluído com sucesso!'}), 200
