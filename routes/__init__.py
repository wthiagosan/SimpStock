from flask import Blueprint

auth_bp = Blueprint('auth', __name__)
produtos_bp = Blueprint('produtos', __name__)
admin_bp = Blueprint('admin', __name__)
movimentacoes_bp = Blueprint('movimentacoes', __name__)

from . import auth_routes
from . import produtos_routes
from . import admin_routes
from . import movimentacoes_routes
