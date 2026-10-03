import concurrent.futures
import pytest
from app import create_app
from database import init_db
from tests.conftest import TestConfig


def test_multi_tenant_sku_isolation(client, user_headers):
    # Lojista A cadastra SKU-GLOBAL-01
    res1 = client.post('/produtos', json={
        'nome': 'Produto Lojista A',
        'marca': 'Marca A',
        'codigo': 'SKU-SHARED-TENANT-01',
        'quantidade': 10
    }, headers=user_headers)
    assert res1.status_code == 201

    # Cria Lojista B
    client.post('/register', json={
        'nome': 'Lojista B',
        'email': 'lojistab_sku@teste.com',
        'senha': 'SenhaForte123'
    })
    res_b = client.post('/login', json={
        'email': 'lojistab_sku@teste.com',
        'senha': 'SenhaForte123'
    })
    token_b = res_b.get_json()['token']
    headers_b = {'Authorization': f'Bearer {token_b}'}

    # Em um SaaS Multi-Tenant real, o Lojista B DEVE conseguir cadastrar o mesmo SKU para o seu catálogo
    res2 = client.post('/produtos', json={
        'nome': 'Produto Lojista B',
        'marca': 'Marca B',
        'codigo': 'SKU-SHARED-TENANT-01',
        'quantidade': 5
    }, headers=headers_b)
    assert res2.status_code == 201, f"Falha no isolamento multi-tenant de SKU: {res2.get_json()}"

    # No entanto, o mesmo lojista (Lojista A) NÃO pode cadastrar o mesmo SKU duplicado para si mesmo
    res3 = client.post('/produtos', json={
        'nome': 'Outro Produto Lojista A',
        'marca': 'Marca A',
        'codigo': 'SKU-SHARED-TENANT-01',
        'quantidade': 2
    }, headers=user_headers)
    assert res3.status_code == 409
    assert 'sku' in res3.get_json()['message'].lower()


def test_prevent_negative_stock_via_atomic_movement(client, user_headers):
    res_prod = client.post('/produtos', json={
        'nome': 'Item Estoque Limitado',
        'marca': 'Marca X',
        'codigo': 'SKU-LIM-01',
        'quantidade': 5
    }, headers=user_headers)
    prod_id = res_prod.get_json()['produto']['id']

    # Tenta dar baixa de 10 unidades (disponível é 5)
    res_saida = client.post(f'/produtos/{prod_id}/movimentar', json={
        'tipo': 'saida',
        'quantidade': 10,
        'motivo': 'Tentativa de venda acima do saldo'
    }, headers=user_headers)

    assert res_saida.status_code == 400
    assert 'insuficiente' in res_saida.get_json()['message'].lower()

    # Verifica se a quantidade se manteve intacta
    res_check = client.get('/produtos', headers=user_headers)
    item = next(p for p in res_check.get_json() if p['id'] == prod_id)
    assert item['quantidade'] == 5


def test_concurrent_stock_dispatch_race_condition(app, temp_db_path):
    # Setup de produto com 10 unidades
    init_client = app.test_client()
    init_client.post('/register', json={
        'nome': 'Lojista Concorrente',
        'email': 'concorrente@teste.com',
        'senha': 'SenhaForte123'
    })
    res_login = init_client.post('/login', json={
        'email': 'concorrente@teste.com',
        'senha': 'SenhaForte123'
    })
    token = res_login.get_json()['token']
    headers = {'Authorization': f'Bearer {token}'}

    res_prod = init_client.post('/produtos', json={
        'nome': 'PlayStation 5 Estoque Concorrente',
        'marca': 'Sony',
        'codigo': 'SKU-PS5-CONC',
        'quantidade': 10
    }, headers=headers)
    assert res_prod.status_code == 201
    prod_id = res_prod.get_json()['produto']['id']

    # Dispara 10 requisições simultâneas de baixa de 2 unidades cada (Demanda total = 20)
    # Com 10 unidades disponíveis, exatamente 5 requisições devem ter sucesso e 5 devem falhar por saldo insuficiente.
    # O saldo final DEVE ser 0, nunca negativo.
    num_threads = 10
    qtd_por_saida = 2

    def execute_dispatch():
        client = app.test_client()
        return client.post(f'/produtos/{prod_id}/movimentar', json={
            'tipo': 'saida',
            'quantidade': qtd_por_saida,
            'motivo': 'Baixa concorrente'
        }, headers=headers)

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(execute_dispatch) for _ in range(num_threads)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    status_codes = [r.status_code for r in results]
    success_count = status_codes.count(200)
    failed_count = status_codes.count(400)

    # Validação estrita de consistência ACID:
    # 5 saídas de 2 = 10 unidades consumidas
    assert success_count == 5, f"Esperado 5 sucessos, obtido {success_count}. Status: {status_codes}"
    assert failed_count == 5, f"Esperado 5 falhas (400), obtido {failed_count}. Status: {status_codes}"

    # Valida saldo final no banco
    res_final = init_client.get('/produtos', headers=headers)
    final_prod = next(p for p in res_final.get_json() if p['id'] == prod_id)
    assert final_prod['quantidade'] == 0


def test_admin_delete_user_with_products_returns_conflict(client, admin_headers):
    # Cria usuário e adiciona produto a ele
    client.post('/register', json={
        'nome': 'Lojista Com Estoque',
        'email': 'lojista_com_estoque@teste.com',
        'senha': 'SenhaForte123'
    })
    res_login = client.post('/login', json={
        'email': 'lojista_com_estoque@teste.com',
        'senha': 'SenhaForte123'
    })
    token = res_login.get_json()['token']
    u_headers = {'Authorization': f'Bearer {token}'}

    res_p = client.post('/produtos', json={
        'nome': 'Item do Lojista',
        'marca': 'Marca Z',
        'codigo': 'SKU-USER-DEL-01',
        'quantidade': 3
    }, headers=u_headers)
    assert res_p.status_code == 201

    res_users = client.get('/usuarios', headers=admin_headers)
    target = next(u for u in res_users.get_json() if u['email'] == 'lojista_com_estoque@teste.com')

    # Admin tenta deletar lojista que possui produtos ativos
    # Não deve crashar com 500, deve retornar 409 Conflict tratado
    res_del = client.delete(f'/usuarios/{target["id"]}', headers=admin_headers)
    assert res_del.status_code == 409
    assert 'possui produtos' in res_del.get_json()['message'].lower() or 'não é possível' in res_del.get_json()['message'].lower()
