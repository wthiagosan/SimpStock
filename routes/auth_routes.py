import sqlite3
from flask import request, jsonify, g
from . import auth_bp
from database import get_db, row_to_dict
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
        db.execute(
            'INSERT INTO usuarios (nome, email, senha, is_admin) VALUES (?, ?, ?, 0)',
            (nome, email, hashed_pwd)
        )
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

        token = generate_token(
            user_id=user['id'],
            nome=user['nome'],
            email=user['email'],
            is_admin=bool(user['is_admin'])
        )

        return jsonify({
            'message': 'Login autorizado!',
            'token': token,
            'usuario': user['nome'],
            'usuario_id': user['id'],
            'is_admin': bool(user['is_admin']),
        }), 200

    return jsonify({'message': 'Email ou senha incorretos.'}), 401


@auth_bp.route('/me', methods=['GET'])
@token_required
def me():
    return jsonify({
        'usuario': g.user['nome'],
        'usuario_id': g.user['id'],
        'email': g.user['email'],
        'is_admin': bool(g.user['is_admin'])
    }), 200
