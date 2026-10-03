import pytest


def test_superadmin_overview_and_access_control(client, admin_headers, user_headers):
    # Superadmin acessa com sucesso
    res_admin = client.get('/superadmin/overview', headers=admin_headers)
    assert res_admin.status_code == 200
    data = res_admin.get_json()
    assert data['status'] == 'success'
    assert 'total_organizations' in data['overview']
    assert 'total_users' in data['overview']
    assert data['overview']['total_organizations'] >= 1

    # Usuário comum recebe 403 Forbidden
    res_user = client.get('/superadmin/overview', headers=user_headers)
    assert res_user.status_code == 403
    assert 'superadmin' in res_user.get_json()['message'].lower()


def test_superadmin_create_and_update_organization(client, admin_headers, user_headers):
    # Criação de organização pelo Superadmin
    new_org_payload = {
        'nome': 'Distribuidora Alfa Express',
        'slug': 'alfa-express',
        'cnpj_ou_documento': '12.345.678/0001-99',
        'plano': 'pro'
    }
    res_create = client.post('/superadmin/organizations', json=new_org_payload, headers=admin_headers)
    assert res_create.status_code == 201
    created_org = res_create.get_json()['organization']
    assert created_org['nome'] == 'Distribuidora Alfa Express'
    assert created_org['slug'] == 'alfa-express'
    assert created_org['plano'] == 'pro'
    org_id = created_org['id']

    # Tentativa de criação por usuário comum deve falhar com 403
    res_unauth = client.post('/superadmin/organizations', json=new_org_payload, headers=user_headers)
    assert res_unauth.status_code == 403

    # Atualização da organização
    update_payload = {
        'nome': 'Distribuidora Alfa Global',
        'plano': 'enterprise',
        'ativo': True
    }
    res_update = client.put(f'/superadmin/organizations/{org_id}', json=update_payload, headers=admin_headers)
    assert res_update.status_code == 200
    assert res_update.get_json()['organization']['nome'] == 'Distribuidora Alfa Global'
    assert res_update.get_json()['organization']['plano'] == 'enterprise'


def test_organization_data_isolation(client, admin_headers):
    # 1. Cria duas organizações separadas
    res_org1 = client.post('/superadmin/organizations', json={
        'nome': 'Empresa Sul Log', 'slug': 'sul-log'
    }, headers=admin_headers)
    org1_id = res_org1.get_json()['organization']['id']

    res_org2 = client.post('/superadmin/organizations', json={
        'nome': 'Empresa Norte Log', 'slug': 'norte-log'
    }, headers=admin_headers)
    org2_id = res_org2.get_json()['organization']['id']

    # 2. Cria dois usuários
    client.post('/register', json={'nome': 'Operador Sul', 'email': 'sul@empresa.com', 'senha': 'Senha123'})
    client.post('/register', json={'nome': 'Operador Norte', 'email': 'norte@empresa.com', 'senha': 'Senha123'})

    # 3. Vincula cada usuário à sua respectiva organização
    client.post('/organizations/current/users', json={'email': 'sul@empresa.com', 'role': 'org_admin'},
                headers={**admin_headers, 'X-Organization-Id': str(org1_id)})
    client.post('/organizations/current/users', json={'email': 'norte@empresa.com', 'role': 'org_admin'},
                headers={**admin_headers, 'X-Organization-Id': str(org2_id)})

    # 4. Login do Operador Sul
    res_login_sul = client.post('/login', json={'email': 'sul@empresa.com', 'senha': 'Senha123'})
    token_sul = res_login_sul.get_json()['token']
    headers_sul = {'Authorization': f'Bearer {token_sul}', 'X-Organization-Id': str(org1_id)}

    # 5. Login do Operador Norte
    res_login_norte = client.post('/login', json={'email': 'norte@empresa.com', 'senha': 'Senha123'})
    token_norte = res_login_norte.get_json()['token']
    headers_norte = {'Authorization': f'Bearer {token_norte}', 'X-Organization-Id': str(org2_id)}

    # 6. Operador Sul cadastra um produto
    res_prod_sul = client.post('/produtos', json={
        'nome': 'Caixa Palete Sul',
        'marca': 'SulMadeiras',
        'codigo': 'SKU-SUL-01',
        'quantidade': 50,
        'custo_unitario': 20.0
    }, headers=headers_sul)
    assert res_prod_sul.status_code == 201

    # 7. Operador Norte NÃO deve ver o produto do Sul
    res_list_norte = client.get('/produtos', headers=headers_norte)
    assert res_list_norte.status_code == 200
    prods_norte = res_list_norte.get_json()
    assert len(prods_norte) == 0

    # 8. Operador Norte cadastra seu próprio produto
    client.post('/produtos', json={
        'nome': 'Empilhadeira Norte',
        'marca': 'NorteMachines',
        'codigo': 'SKU-NORTE-01',
        'quantidade': 3,
        'custo_unitario': 15000.0
    }, headers=headers_norte)

    # 9. Operador Sul NÃO deve ver o produto do Norte
    res_list_sul = client.get('/produtos', headers=headers_sul)
    prods_sul = res_list_sul.get_json()
    assert len(prods_sul) == 1
    assert prods_sul[0]['codigo'] == 'SKU-SUL-01'


def test_superadmin_impersonation_and_audit_trail(client, admin_headers):
    # 1. Cria organização alvo
    res_org = client.post('/superadmin/organizations', json={
        'nome': 'Farmácia Vida Longa', 'slug': 'farmacia-vida'
    }, headers=admin_headers)
    org_id = res_org.get_json()['organization']['id']

    # 2. Impersonação SEM justificativa deve falhar (400)
    res_fail = client.post('/superadmin/impersonate', json={
        'target_org_id': org_id,
        'reason': ''
    }, headers=admin_headers)
    assert res_fail.status_code == 400
    assert 'justificativa' in res_fail.get_json()['message'].lower()

    # 3. Impersonação COM justificativa válida
    justificativa = "Atendimento ao chamado de suporte técnico #9410 - Investigação de saldo"
    res_impersonate = client.post('/superadmin/impersonate', json={
        'target_org_id': org_id,
        'reason': justificativa
    }, headers=admin_headers)
    assert res_impersonate.status_code == 200
    impersonate_data = res_impersonate.get_json()
    assert 'token' in impersonate_data
    assert impersonate_data['organization']['id'] == org_id

    imp_token = impersonate_data['token']
    imp_headers = {'Authorization': f'Bearer {imp_token}'}

    # 4. Checa `/me` sob impersonação
    res_me = client.get('/me', headers=imp_headers)
    assert res_me.status_code == 200
    me_data = res_me.get_json()
    assert me_data['impersonated_by'] == 1
    assert me_data['organization_id'] == org_id

    # 5. Sob impersonação, cadastra produto na organização do cliente
    res_prod = client.post('/produtos', json={
        'nome': 'Termômetro Digital Clínico',
        'marca': 'G-Tech',
        'codigo': 'SKU-MED-01',
        'quantidade': 30,
        'custo_unitario': 25.5
    }, headers=imp_headers)
    assert res_prod.status_code == 201

    # 6. Verifica log de auditoria criptográfico
    res_audits = client.get(f'/superadmin/audit-logs?organization_id={org_id}', headers=admin_headers)
    assert res_audits.status_code == 200
    audits = res_audits.get_json()
    assert any(a['acao'] == 'superadmin.impersonate_start' for a in audits)
    audit_entry = next(a for a in audits if a['acao'] == 'superadmin.impersonate_start')
    assert str(org_id) in audit_entry['detalhes']
    assert justificativa in audit_entry['detalhes']


def test_organization_switcher(client, admin_headers):
    # Cria uma segunda organização
    res_org = client.post('/superadmin/organizations', json={
        'nome': 'Boutique Paris Modas', 'slug': 'boutique-paris'
    }, headers=admin_headers)
    org2_id = res_org.get_json()['organization']['id']

    # Superadmin alterna de contexto para a organização 2
    res_switch = client.post('/organizations/switch', json={'organization_id': org2_id}, headers=admin_headers)
    assert res_switch.status_code == 200
    switch_data = res_switch.get_json()
    assert switch_data['organization']['id'] == org2_id
    new_token = switch_data['token']

    # Verifica se novo token reflete a nova organização
    res_me = client.get('/me', headers={'Authorization': f'Bearer {new_token}'})
    assert res_me.status_code == 200
    assert res_me.get_json()['organization_id'] == org2_id


def test_executive_kpis_endpoint(client, user_headers):
    # Cadastra itens com diferentes custos e níveis de estoque
    client.post('/produtos', json={
        'nome': 'Item Estoque Saudável',
        'marca': 'Marca A',
        'codigo': 'SKU-KPI-01',
        'quantidade': 20,
        'estoque_minimo': 5,
        'custo_unitario': 10.0,
        'preco_venda': 25.0
    }, headers=user_headers)

    client.post('/produtos', json={
        'nome': 'Item Em Ruptura',
        'marca': 'Marca B',
        'codigo': 'SKU-KPI-02',
        'quantidade': 0,
        'estoque_minimo': 5,
        'custo_unitario': 50.0,
        'preco_venda': 100.0
    }, headers=user_headers)

    client.post('/produtos', json={
        'nome': 'Item Estoque Crítico',
        'marca': 'Marca C',
        'codigo': 'SKU-KPI-03',
        'quantidade': 3,
        'estoque_minimo': 5,
        'custo_unitario': 30.0,
        'preco_venda': 60.0
    }, headers=user_headers)

    res_kpis = client.get('/produtos/kpis', headers=user_headers)
    assert res_kpis.status_code == 200
    kpis = res_kpis.get_json()

    assert kpis['total_skus'] == 3
    assert kpis['total_itens'] == 23
    # 20 * 10.0 + 0 * 50.0 + 3 * 30.0 = 200 + 0 + 90 = 290.0
    assert kpis['valor_imobilizado'] == 290.0
    # 20 * 25.0 + 0 * 100.0 + 3 * 60.0 = 500 + 0 + 180 = 680.0
    assert kpis['valor_venda_potencial'] == 680.0
    assert kpis['itens_esgotados'] == 1
    assert kpis['itens_baixo_estoque'] == 1
    assert kpis['itens_saudaveis'] == 1
    assert len(kpis['movimentacoes_recentes']) >= 2
