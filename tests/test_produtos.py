def test_create_product(client, user_headers):
    payload = {
        'nome': 'Teclado Mecânico RGB',
        'marca': 'Keychron',
        'codigo': 'SKU-KEY-01',
        'quantidade': 25,
        'referencia': 'REF-K2',
        'validade': None,
        'endereco': 'Corredor B, Prateleira 4'
    }
    res = client.post('/produtos', json=payload, headers=user_headers)
    assert res.status_code == 201
    data = res.get_json()
    assert data['produto']['nome'] == 'Teclado Mecânico RGB'
    assert data['produto']['quantidade'] == 25


def test_create_product_duplicate_sku(client, user_headers):
    payload = {
        'nome': 'Mouse Gamer',
        'marca': 'Logitech',
        'codigo': 'SKU-MOUSE-01',
        'quantidade': 10
    }
    res1 = client.post('/produtos', json=payload, headers=user_headers)
    assert res1.status_code == 201

    res2 = client.post('/produtos', json=payload, headers=user_headers)
    assert res2.status_code == 409
    assert 'código sku' in res2.get_json()['message'].lower()


def test_user_product_isolation(client, user_headers, admin_headers):
    # Cadastra produto com usuario comum
    client.post('/produtos', json={
        'nome': 'Monitor 27 UltraWide',
        'marca': 'LG',
        'codigo': 'SKU-MON-27',
        'quantidade': 5
    }, headers=user_headers)

    # Cria segundo lojista
    client.post('/register', json={
        'nome': 'Lojista B',
        'email': 'lojistab@teste.com',
        'senha': 'SenhaForte123'
    })
    res_b = client.post('/login', json={
        'email': 'lojistab@teste.com',
        'senha': 'SenhaForte123'
    })
    token_b = res_b.get_json()['token']
    headers_b = {'Authorization': f'Bearer {token_b}'}

    # Lojista B deve ver 0 produtos (não pode ver produtos do Lojista A!)
    res_list_b = client.get('/produtos', headers=headers_b)
    assert res_list_b.status_code == 200
    produtos_b = res_list_b.get_json()
    assert len(produtos_b) == 0

    # Admin deve conseguir ver todos os produtos
    res_admin = client.get('/produtos', headers=admin_headers)
    assert res_admin.status_code == 200
    assert len(res_admin.get_json()) > 0


def test_prevent_idor_on_update(client, user_headers):
    # Cria produto com o usuário A
    res = client.post('/produtos', json={
        'nome': 'Notebook Gamer',
        'marca': 'Dell',
        'codigo': 'SKU-DELL-G15',
        'quantidade': 8
    }, headers=user_headers)
    prod_id = res.get_json()['produto']['id']

    # Loga com usuário B
    client.post('/register', json={
        'nome': 'Invasor',
        'email': 'invasor@teste.com',
        'senha': 'SenhaInvasor123'
    })
    token_invasor = client.post('/login', json={
        'email': 'invasor@teste.com',
        'senha': 'SenhaInvasor123'
    }).get_json()['token']

    # Invasor tenta alterar o produto do usuário A -> deve ser 403 Forbidden!
    res_update = client.put(f'/produtos/{prod_id}', json={
        'nome': 'Hacked Product',
        'quantidade': 999
    }, headers={'Authorization': f'Bearer {token_invasor}'})

    assert res_update.status_code == 403
    assert 'sem permissão' in res_update.get_json()['message'].lower()


def test_movimentacoes_audit(client, user_headers):
    res_prod = client.post('/produtos', json={
        'nome': 'Cadeira Ergonômica',
        'marca': 'Flexform',
        'codigo': 'SKU-CAD-01',
        'quantidade': 10
    }, headers=user_headers)
    prod_id = res_prod.get_json()['produto']['id']

    # Atualiza quantidade (adiciona +5)
    client.put(f'/produtos/{prod_id}', json={
        'quantidade': 15,
        'motivo': 'Chegada de novo lote'
    }, headers=user_headers)

    res_mov = client.get(f'/movimentacoes?produto_id={prod_id}', headers=user_headers)
    assert res_mov.status_code == 200
    movs = res_mov.get_json()
    assert len(movs) == 2  # Entrada inicial + atualização
    assert movs[0]['tipo'] == 'entrada'
