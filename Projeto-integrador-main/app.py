import json
import os
import re
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# --- CONFIGURAÇÃO DE CAMINHOS (CORREÇÃO PARA SERVIDOR) ---
# Isso garante que o servidor encontre os arquivos JSON na pasta certa
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ARQUIVO_DB = os.path.join(BASE_DIR, 'banco.json')
ARQUIVO_USUARIOS = os.path.join(BASE_DIR, 'usuarios.json')

# --- ROTA INICIAL (NOVA) ---
@app.route('/')
def home():
    return "SIMPSTOCK ONLINE"

# --- Funções Auxiliares ---
def carregar_json(arquivo):
    if not os.path.exists(arquivo): return []
    try:
        with open(arquivo, 'r', encoding='utf-8') as f: return json.load(f)
    except: return []

def salvar_json(arquivo, dados):
    with open(arquivo, 'w', encoding='utf-8') as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)

def gerar_novo_id(lista):
    if not lista: return 1
    # Pega o maior ID da lista e soma 1 (evita duplicatas)
    return max(item['id'] for item in lista) + 1

def senha_valida(senha):
    regra = r'^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]{6,}$'
    return re.match(regra, senha)

# --- Rotas de PRODUTOS ---
@app.route('/produtos', methods=['GET'])
def get_produtos(): return jsonify(carregar_json(ARQUIVO_DB))

@app.route('/produtos', methods=['POST'])
def add_produto():
    produtos = carregar_json(ARQUIVO_DB)
    data = request.get_json()
    
    novo_produto = {
        "id": gerar_novo_id(produtos),
        "nome": data.get('nome'), "marca": data.get('marca'),
        "validade": data.get('validade'), "codigo": data.get('codigo'),
        "quantidade": data.get('quantidade'), "referencia": data.get('referencia'),
        "endereco": data.get('endereco')
    }
    produtos.append(novo_produto)
    salvar_json(ARQUIVO_DB, produtos)
    return jsonify({"message": "Sucesso!", "produto": novo_produto}), 201

@app.route('/produtos/<int:id_produto>', methods=['PUT'])
def update_produto(id_produto):
    produtos = carregar_json(ARQUIVO_DB)
    data = request.get_json()
    for produto in produtos:
        if produto['id'] == id_produto:
            produto.update(data)
            salvar_json(ARQUIVO_DB, produtos)
            return jsonify({"message": "Atualizado!"}), 200
    return jsonify({"message": "Produto não encontrado"}), 404

@app.route('/produtos/<int:id_produto>', methods=['DELETE'])
def delete_produto(id_produto):
    produtos = carregar_json(ARQUIVO_DB)
    nova_lista = [p for p in produtos if p['id'] != id_produto]
    if len(produtos) == len(nova_lista): return jsonify({"message": "Produto não encontrado"}), 404
    salvar_json(ARQUIVO_DB, nova_lista)
    return jsonify({"message": "Deletado!"}), 200

# --- Rotas de USUÁRIOS ---

@app.route('/register', methods=['POST'])
def register():
    usuarios = carregar_json(ARQUIVO_USUARIOS)
    data = request.get_json()
    email = data.get('email')
    senha = data.get('senha')
    nome = data.get('nome')

    if not senha_valida(senha):
        return jsonify({"message": "Senha inválida! Use letras e números (sem especiais)."}), 400

    for user in usuarios:
        if user['email'] == email:
            return jsonify({"message": "Email já cadastrado!"}), 400

    novo_usuario = {
        "id": gerar_novo_id(usuarios),
        "nome": nome, "email": email, "senha": senha, "is_admin": False 
    }
    usuarios.append(novo_usuario)
    salvar_json(ARQUIVO_USUARIOS, usuarios)
    return jsonify({"message": "Usuário criado com sucesso!"}), 201

@app.route('/login', methods=['POST'])
def login():
    usuarios = carregar_json(ARQUIVO_USUARIOS)
    data = request.get_json()
    for user in usuarios:
        if user['email'] == data.get('email') and user['senha'] == data.get('senha'):
            return jsonify({
                "message": "Login autorizado!", 
                "usuario": user['nome'],
                "is_admin": user.get('is_admin', False)
            }), 200
    return jsonify({"message": "Email ou senha incorretos."}), 401

# --- Rotas ADMIN ---
@app.route('/usuarios', methods=['GET'])
def get_usuarios():
    usuarios = carregar_json(ARQUIVO_USUARIOS)
    safe_users = [{"id": u["id"], "nome": u["nome"], "email": u["email"], "is_admin": u.get("is_admin", False)} for u in usuarios]
    return jsonify(safe_users)

@app.route('/usuarios/<int:id_usuario>', methods=['DELETE'])
def delete_usuario(id_usuario):
    usuarios = carregar_json(ARQUIVO_USUARIOS)
    
    if id_usuario == 1: # Protege o Admin Principal
        return jsonify({"message": "Não é possível excluir o Administrador Principal!"}), 403

    nova_lista = [u for u in usuarios if u['id'] != id_usuario]
    
    if len(usuarios) == len(nova_lista): 
        return jsonify({"message": "Usuário não encontrado"}), 404
        
    salvar_json(ARQUIVO_USUARIOS, nova_lista)
    return jsonify({"message": "Usuário deletado!"}), 200

if __name__ == '__main__':
    # Em produção (PythonAnywhere), isso aqui é ignorado, mas ajuda no teste local
    app.run(debug=True, port=5000)
