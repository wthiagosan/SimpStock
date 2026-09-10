import os
from flask import Flask, jsonify
from flask_cors import CORS
from config import Config
from database import close_db, init_db
from routes import auth_bp, produtos_bp, admin_bp, movimentacoes_bp


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Configuração do CORS
    CORS(app, origins=config_class.CORS_ORIGINS)

    # Teardown de conexão de banco
    app.teardown_appcontext(close_db)

    # Registro de rotas e Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(produtos_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(movimentacoes_bp)

    @app.route('/', methods=['GET'])
    def health_check():
        return jsonify({
            'status': 'online',
            'app': 'SimpStock API',
            'version': '2.0.0',
            'description': 'Sistema de Gestão de Estoque e Inventário'
        }), 200

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'message': 'Recurso não encontrado no servidor.'}), 404

    @app.errorhandler(405)
    def method_not_allowed(error):
        return jsonify({'message': 'Método HTTP não permitido para este endpoint.'}), 405

    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({'message': 'Erro interno do servidor.'}), 500

    return app


app = create_app()


if __name__ == '__main__':
    init_db()
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() in ('true', '1', 't')
    app.run(host='0.0.0.0', port=port, debug=debug)
