from flask import request, jsonify, g
from . import movimentacoes_bp
from database import get_db, rows_to_list
from auth import token_required


@movimentacoes_bp.route('/movimentacoes', methods=['GET'])
@token_required
def get_movimentacoes():
    produto_id = request.args.get('produto_id', type=int)
    db = get_db()
    is_admin = bool(g.user.get('is_admin'))

    base_query = '''
        SELECT m.id, m.produto_id, m.usuario_id, m.tipo, m.quantidade,
               m.motivo, m.criado_em,
               p.nome AS produto_nome,
               u.nome AS usuario_nome
        FROM movimentacoes m
        JOIN produtos p ON p.id = m.produto_id
        JOIN usuarios u ON u.id = m.usuario_id
    '''

    params = []
    conditions = []

    if not is_admin:
        conditions.append('p.usuario_id = ?')
        params.append(g.user['id'])

    if produto_id:
        conditions.append('m.produto_id = ?')
        params.append(produto_id)

    if conditions:
        base_query += ' WHERE ' + ' AND '.join(conditions)

    base_query += ' ORDER BY m.criado_em DESC LIMIT 100'

    rows = db.execute(base_query, params).fetchall()
    return jsonify(rows_to_list(rows)), 200
