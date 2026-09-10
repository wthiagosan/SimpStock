from flask import jsonify, g
from . import admin_bp
from database import get_db, rows_to_list
from auth import admin_required


@admin_bp.route('/usuarios', methods=['GET'])
@admin_required
def get_usuarios():
    db = get_db()
    rows = db.execute(
        'SELECT id, nome, email, is_admin, criado_em FROM usuarios ORDER BY id'
    ).fetchall()

    usuarios = rows_to_list(rows)
    for u in usuarios:
        u['is_admin'] = bool(u['is_admin'])

    return jsonify(usuarios), 200


@admin_bp.route('/usuarios/<int:id_usuario>', methods=['DELETE'])
@admin_required
def delete_usuario(id_usuario):
    if id_usuario == 1:
        return jsonify({'message': 'Operação negada! Não é permitido excluir o Administrador Principal.'}), 403

    if id_usuario == g.user['id']:
        return jsonify({'message': 'Operação negada! Não é possível excluir seu próprio usuário administrador.'}), 400

    db = get_db()
    cursor = db.execute('DELETE FROM usuarios WHERE id = ?', (id_usuario,))
    if cursor.rowcount == 0:
        return jsonify({'message': 'Usuário não encontrado.'}), 404

    db.commit()
    return jsonify({'message': 'Usuário removido com sucesso!'}), 200
