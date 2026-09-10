import re
from datetime import datetime, timezone, timedelta
from functools import wraps
import jwt
from flask import request, jsonify, g
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config
from database import get_db, row_to_dict


def hash_password(password: str) -> str:
    """Gera hash seguro para a senha com salt criptográfico."""
    return generate_password_hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    """Verifica se a senha em texto plano confere com o hash ou texto plano legado."""
    if not hashed_password.startswith(('scrypt:', 'pbkdf2:')):
        return password == hashed_password
    return check_password_hash(hashed_password, password)


def is_password_valid(password: str) -> bool:
    """Regra de validação: mínimo 6 caracteres contendo ao menos uma letra e um número."""
    if not password or len(password) < 6:
        return False
    return bool(re.search(r'[A-Za-z]', password) and re.search(r'\d', password))


def generate_token(user_id: int, nome: str, email: str, is_admin: bool) -> str:
    """Emite um JSON Web Token (JWT) assinado com HS256 e expiração configurada."""
    now = datetime.now(timezone.utc)
    payload = {
        'sub': str(user_id),
        'user_id': user_id,
        'nome': nome,
        'email': email,
        'is_admin': bool(is_admin),
        'exp': now + timedelta(hours=Config.JWT_EXPIRATION_HOURS),
        'iat': now
    }
    return jwt.encode(payload, Config.JWT_SECRET, algorithm='HS256')


def decode_token(token: str) -> dict:
    """Decodifica e valida a assinatura e expiração do token JWT."""
    return jwt.decode(token, Config.JWT_SECRET, algorithms=['HS256'])


def token_required(f):
    """Decorator para exigir autenticação JWT e injetar o usuário autenticado em flask.g.user."""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get('Authorization', '')

        if auth_header.startswith('Bearer '):
            token = auth_header.split(' ', 1)[1].strip()
        elif 'token' in request.args:
            token = request.args.get('token')

        if not token:
            return jsonify({'message': 'Acesso não autorizado. Token JWT ausente.'}), 401

        try:
            payload = decode_token(token)
            db = get_db()
            user = row_to_dict(db.execute(
                "SELECT id, nome, email, is_admin FROM usuarios WHERE id = ?",
                (payload['user_id'],)
            ).fetchone())

            if not user:
                return jsonify({'message': 'Usuário associado ao token não foi encontrado.'}), 401

            g.user = user
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Sessão expirada. Por favor, autentique-se novamente.'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Token de autenticação inválido.'}), 401

        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    """Decorator para exigir perfil de administrador no token JWT autenticado."""
    @wraps(f)
    @token_required
    def decorated(*args, **kwargs):
        if not g.user.get('is_admin'):
            return jsonify({'message': 'Acesso negado. Requer privilégios de Administrador.'}), 403
        return f(*args, **kwargs)
    return decorated
