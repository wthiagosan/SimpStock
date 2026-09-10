def test_health_check(client):
    res = client.get('/')
    assert res.status_code == 200
    data = res.get_json()
    assert data['status'] == 'online'
    assert 'SimpStock' in data['app']


def test_register_success(client):
    res = client.post('/register', json={
        'nome': 'Maria Santos',
        'email': 'maria@lojista.com',
        'senha': 'SenhaValida1'
    })
    assert res.status_code == 201
    assert 'sucesso' in res.get_json()['message'].lower()


def test_register_duplicate_email(client):
    payload = {
        'nome': 'Carlos Silva',
        'email': 'carlos@empresa.com',
        'senha': 'SenhaForte123'
    }
    client.post('/register', json=payload)
    res = client.post('/register', json=payload)
    assert res.status_code == 400
    assert 'já está cadastrado' in res.get_json()['message'].lower()


def test_register_invalid_password(client):
    res = client.post('/register', json={
        'nome': 'Teste Invalido',
        'email': 'invalido@teste.com',
        'senha': '123'  # Menos de 6 caracteres e sem letras
    })
    assert res.status_code == 400
    assert 'senha inválida' in res.get_json()['message'].lower()


def test_login_success(client):
    res = client.post('/login', json={
        'email': 'admin@simpstock.com',
        'senha': 'admin123'
    })
    assert res.status_code == 200
    data = res.get_json()
    assert 'token' in data
    assert data['usuario_id'] == 1
    assert data['is_admin'] is True


def test_login_wrong_password(client):
    res = client.post('/login', json={
        'email': 'admin@simpstock.com',
        'senha': 'senha_errada'
    })
    assert res.status_code == 401


def test_me_protected_route(client, user_headers):
    # Sem token -> 401
    res = client.get('/me')
    assert res.status_code == 401

    # Com token válido -> 200
    res = client.get('/me', headers=user_headers)
    assert res.status_code == 200
    data = res.get_json()
    assert data['email'] == 'lojista@teste.com'
