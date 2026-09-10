def test_admin_list_users(client, admin_headers):
    res = client.get('/usuarios', headers=admin_headers)
    assert res.status_code == 200
    users = res.get_json()
    assert len(users) > 0
    # Valida que o campo senha NÃO é exposto
    for u in users:
        assert 'senha' not in u
        assert 'email' in u
        assert 'is_admin' in u


def test_regular_user_blocked_from_admin(client, user_headers):
    res = client.get('/usuarios', headers=user_headers)
    assert res.status_code == 403
    assert 'acesso negado' in res.get_json()['message'].lower()


def test_cannot_delete_master_admin(client, admin_headers):
    res = client.delete('/usuarios/1', headers=admin_headers)
    assert res.status_code == 403
    assert 'não é permitido excluir' in res.get_json()['message'].lower()


def test_admin_can_delete_user(client, admin_headers):
    # Cria usuário para teste de remoção
    client.post('/register', json={
        'nome': 'Usuario Deletavel',
        'email': 'deletavel@teste.com',
        'senha': 'Senha123'
    })
    res_list = client.get('/usuarios', headers=admin_headers)
    target = next(u for u in res_list.get_json() if u['email'] == 'deletavel@teste.com')
    target_id = target['id']

    res_del = client.delete(f'/usuarios/{target_id}', headers=admin_headers)
    assert res_del.status_code == 200
    assert 'removido com sucesso' in res_del.get_json()['message'].lower()
