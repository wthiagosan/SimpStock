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


def generate_token(user_id: int, nome: str, email: str, is_admin: bool,
                   is_superadmin: bool = False, org_id: int = None,
                   org_role: str = None, impersonated_by: int = None,
                   expires_hours: float = None) -> str:
    """Emite um JSON Web Token (JWT) assinado com HS256, escopo multi-tenant e auditoria de impersonação."""
    now = datetime.now(timezone.utc)
    exp_hours = expires_hours if expires_hours is not None else Config.JWT_EXPIRATION_HOURS
    payload = {
        'sub': str(user_id),
        'user_id': user_id,
        'nome': nome,
        'email': email,
        'is_admin': bool(is_admin),
        'is_superadmin': bool(is_superadmin),
        'org_id': org_id,
        'org_role': org_role,
        'impersonated_by': impersonated_by,
        'exp': now + timedelta(hours=exp_hours),
        'iat': now
    }
    return jwt.encode(payload, Config.JWT_SECRET, algorithm='HS256')


def decode_token(token: str) -> dict:
    """Decodifica e valida a assinatura e expiração do token JWT."""
    return jwt.decode(token, Config.JWT_SECRET, algorithms=['HS256'])


def token_required(f):
    """Decorator para exigir autenticação JWT e injetar o contexto do usuário e da organização em flask.g."""
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
                "SELECT id, nome, email, is_admin, is_superadmin FROM usuarios WHERE id = ?",
                (payload['user_id'],)
            ).fetchone())

            if not user:
                return jsonify({'message': 'Usuário associado ao token não foi encontrado.'}), 401

            user['is_admin'] = bool(user.get('is_admin', 0))
            user['is_superadmin'] = bool(user.get('is_superadmin', 0)) or (user['id'] == 1)
            g.user = user

            # Injeção e resolução do Tenant Context (Organization)
            token_org_id = payload.get('org_id')
            header_org_id = request.headers.get('X-Organization-Id')
            query_org_id = request.args.get('organization_id')

            selected_org_id = None
            if header_org_id and header_org_id.isdigit():
                selected_org_id = int(header_org_id)
            elif query_org_id and query_org_id.isdigit():
                selected_org_id = int(query_org_id)
            elif token_org_id:
                selected_org_id = int(token_org_id)

            # Se não veio na requisição nem no token, busca a primeira organização ativa do usuário
            if selected_org_id is None:
                first_org = db.execute(
                    '''SELECT organization_id, role FROM user_organizations
                       WHERE usuario_id = ? AND ativo = 1 ORDER BY id ASC LIMIT 1''',
                    (user['id'],)
                ).fetchone()
                if first_org:
                    selected_org_id = first_org['organization_id']
                    g.org_role = first_org['role']
                elif user['is_superadmin']:
                    # Superadmin sem vínculo explícito acessa a organização matriz (ID 1)
                    selected_org_id = 1
                    g.org_role = 'superadmin'
                else:
                    selected_org_id = 1
                    g.org_role = 'org_operator'

            # Determina o papel do usuário na organização selecionada
            if not hasattr(g, 'org_role') or g.org_role is None:
                uo_row = db.execute(
                    '''SELECT role FROM user_organizations
                       WHERE usuario_id = ? AND organization_id = ? AND ativo = 1''',
                    (user['id'], selected_org_id)
                ).fetchone()
                if uo_row:
                    g.org_role = uo_row['role']
                elif user['is_superadmin']:
                    g.org_role = 'superadmin'
                elif user['is_admin']:
                    g.org_role = 'org_admin'
                else:
                    g.org_role = 'org_operator'

            g.org_id = selected_org_id
            g.impersonated_by = payload.get('impersonated_by')

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
        if not (g.user.get('is_admin') or g.user.get('is_superadmin')):
            return jsonify({'message': 'Acesso negado. Requer privilégios de Administrador.'}), 403
        return f(*args, **kwargs)
    return decorated


def superadmin_required(f):
    """Decorator para exigir privilégios globais de Superadministrador (Admin Master)."""
    @wraps(f)
    @token_required
    def decorated(*args, **kwargs):
        if not (g.user.get('is_superadmin') or g.user.get('id') == 1):
            return jsonify({'message': 'Acesso negado. Requer privilégios de Administrador Master (Superadmin).'}), 403
        return f(*args, **kwargs)
    return decorated


def org_admin_required(f):
    """Decorator para exigir papel de Administrador da Organização selecionada ou Superadmin."""
    @wraps(f)
    @token_required
    def decorated(*args, **kwargs):
        if not (g.user.get('is_superadmin') or g.user.get('is_admin') or getattr(g, 'org_role', '') in ('superadmin', 'org_admin')):
            return jsonify({'message': 'Acesso negado. Requer privilégios de Administrador da Organização.'}), 403
        return f(*args, **kwargs)
    return decorated
