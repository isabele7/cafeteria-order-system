def criar_produto(client, nome="Cafe", preco=5.0, estoque=10):
    response = client.post(
        "/api/produtos",
        json={"nome": nome, "preco": preco, "estoque": estoque},
    )
    assert response.status_code == 201
    return response.json()

def criar_pedido(client):
    response = client.post("/api/pedidos")
    assert response.status_code == 201
    return response.json()

def adicionar_item(client, pedido_id, produto_id, quantidade):
    return client.post(
        f"/api/pedidos/{pedido_id}/itens",
        json={"produto_id": produto_id, "quantidade": quantidade},
    )

def definir_tipo(client, pedido_id, tipo="retirada"):
    return client.put(
        f"/api/pedidos/{pedido_id}/tipo",
        json={"tipo": tipo},
    )

# Testes de integração para as rotas da API
class TestRootHealth:
    def test_root_retorna_mensagem_da_api(self, client):
        response = client.get("/")

        assert response.status_code == 200
        assert response.json()["mensagem"] == "Sistema de pedidos de cafeteria"

    def test_health_retorna_status_ok(self, client):
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

# Testes de integração para as rotas de produtos, cupons e pedidos
class TestProdutosRoutes:
    def test_criar_produto(self, client):
        data = criar_produto(client, nome="Cafe", preco=5.0, estoque=10)

        assert data["nome"] == "Cafe"
        assert data["preco"] == 5.0
        assert data["estoque"] == 10
        
    def test_listar_produtos(self, client):
        criar_produto(client, nome="Cafe", preco=5.0, estoque=10)
        criar_produto(client, nome="Bolo", preco=8.0, estoque=5)

        response = client.get("/api/produtos")

        assert response.status_code == 200
        assert len(response.json()) == 2
    
    def test_atualizar_produto_existente(self, client):
        produto = criar_produto(client, nome="Cafe", preco=5.0, estoque=10)

        response = client.put(
            f"/api/produtos/{produto['id']}",
            json={"nome": "Cafe Especial", "preco": 6.5, "estoque": 15},
        )

        assert response.status_code == 200
        assert response.json()["nome"] == "Cafe Especial"
        assert response.json()["preco"] == 6.5
        assert response.json()["estoque"] == 15

    def test_criar_produto_duplicado_retorna_409(self, client):
        criar_produto(client, nome="Cafe", preco=5.0, estoque=10)

        response = client.post(
            "/api/produtos",
            json={"nome": "Cafe", "preco": 6.0, "estoque": 5},
        )

        assert response.status_code == 409
        assert response.json()["detail"] == "Produto já existe."

    def test_obter_produto_inexistente_retorna_404(self, client):
        response = client.get("/api/produtos/999")

        assert response.status_code == 404
        assert response.json()["detail"] == "Produto não encontrado."

    def test_atualizar_produto_inexistente_retorna_404(self, client):
        response = client.put("/api/produtos/999", json={"preco": 9.0})

        assert response.status_code == 404
        assert response.json()["detail"] == "Produto não encontrado."

    def test_deletar_produto_inexistente_retorna_404(self, client):
        response = client.delete("/api/produtos/999")

        assert response.status_code == 404
        assert response.json()["detail"] == "Produto não encontrado."

class TestCuponsRoutes:
    def test_criar_e_listar_cupom(self, client):
        response = client.post(
            "/api/cupons",
            json={"codigo": "DESC10", "desconto": 10.0, "minimo": 50.0},
        )

        assert response.status_code == 201
        assert response.json()["codigo"] == "DESC10"

        listar = client.get("/api/cupons")
        assert listar.status_code == 200
        assert len(listar.json()) == 1

    def test_obter_cupom_inexistente_retorna_404(self, client):
        response = client.get("/api/cupons/999")

        assert response.status_code == 404
        assert response.json()["detail"] == "Cupom não encontrado"

class TestPedidosRoutes:
    def test_criar_pedido(self, client):
        data = criar_pedido(client)

        assert data["status"] == "criado"
        assert data["subtotal"] == 0.0
        assert data["total"] == 0.0

    def test_adicionar_item_valido_atualiza_subtotal(self, client):
        produto = criar_produto(client, nome="Cafe", preco=5.0, estoque=10)
        pedido = criar_pedido(client)

        response = adicionar_item(client, pedido["id"], produto["id"], 3)

        assert response.status_code == 201
        assert response.json()["quantidade"] == 3
        assert response.json()["subtotal"] == 15.0

        detalhe = client.get(f"/api/pedidos/{pedido['id']}")
        assert detalhe.status_code == 200
        assert detalhe.json()["subtotal"] == 15.0

    def test_adicionar_item_sem_estoque_retorna_400(self, client):
        produto = criar_produto(client, nome="Suco", preco=7.0, estoque=0)
        pedido = criar_pedido(client)

        response = adicionar_item(client, pedido["id"], produto["id"], 1)

        assert response.status_code == 400
        assert response.json()["detail"] == "Estoque insuficiente. Disponível: 0"

    def test_adicionar_item_quantidade_zero_retorna_400(self, client):
        produto = criar_produto(client, nome="Cafe", preco=5.0, estoque=10)
        pedido = criar_pedido(client)

        response = adicionar_item(client, pedido["id"], produto["id"], 0)

        assert response.status_code == 400
        assert response.json()["detail"] == "Quantidade inválida"

    def test_remover_item_de_outro_pedido_retorna_400(self, client):
        produto = criar_produto(client, nome="Cafe", preco=5.0, estoque=10)
        pedido_com_item = criar_pedido(client)
        outro_pedido = criar_pedido(client)
        item_response = adicionar_item(client, pedido_com_item["id"], produto["id"], 2)
        assert item_response.status_code == 201
        item_id = item_response.json()["id"]

        response = client.delete(f"/api/pedidos/{outro_pedido['id']}/itens/{item_id}")

        assert response.status_code == 400
        assert response.json()["detail"] == "Item não pertence ao pedido informado"

    def test_aplicar_cupom_valido(self, client):
        client.post("/api/cupons", json={"codigo": "DESC10", "desconto": 10.0, "minimo": 50.0})
        produto = criar_produto(client, nome="Cafe", preco=5.0, estoque=20)
        pedido = criar_pedido(client)
        adicionar_item(client, pedido["id"], produto["id"], 10)

        response = client.post(f"/api/pedidos/{pedido['id']}/cupom", json={"codigo": "DESC10"})

        assert response.status_code == 200
        assert response.json()["mensagem"] == "Cupom aplicado: R$5.00 de desconto"

    def test_aplicar_cupom_inexistente_retorna_400(self, client):
        pedido = criar_pedido(client)

        response = client.post(f"/api/pedidos/{pedido['id']}/cupom", json={"codigo": "NAO_EXISTE"})

        assert response.status_code == 400
        assert response.json()["detail"] == "Cupom não encontrado"

    def test_definir_tipo_entrega_com_taxa(self, client):
        produto = criar_produto(client, nome="Cafe", preco=5.0, estoque=10)
        pedido = criar_pedido(client)
        adicionar_item(client, pedido["id"], produto["id"], 2)

        response = definir_tipo(client, pedido["id"], "entrega")

        assert response.status_code == 200
        detalhe = client.get(f"/api/pedidos/{pedido['id']}")
        assert detalhe.json()["taxa_entrega"] == 10.0
        assert detalhe.json()["total"] == 20.0

    def test_finalizar_pedido_sem_item_retorna_400(self, client):
        pedido = criar_pedido(client)
        definir_tipo(client, pedido["id"], "retirada")

        response = client.post(f"/api/pedidos/{pedido['id']}/finalizar")

        assert response.status_code == 400
        assert response.json()["detail"] == "Pedido precisa ter pelo menos um item para finalizar"

    def test_finalizar_pedido_valido(self, client):
        produto = criar_produto(client, nome="Cafe", preco=5.0, estoque=10)
        pedido = criar_pedido(client)
        adicionar_item(client, pedido["id"], produto["id"], 2)
        definir_tipo(client, pedido["id"], "retirada")

        response = client.post(f"/api/pedidos/{pedido['id']}/finalizar")

        assert response.status_code == 200
        assert response.json()["mensagem"] == "Pedido finalizado. Total: R$10.00"
        detalhe = client.get(f"/api/pedidos/{pedido['id']}")
        assert detalhe.json()["status"] == "pago"

    def test_obter_pedido_inexistente_retorna_404(self, client):
        response = client.get("/api/pedidos/999")

        assert response.status_code == 404
        assert response.json()["detail"] == "Pedido não encontrado"

    def test_cancelar_pedido(self, client):
        pedido = criar_pedido(client)

        response = client.post(f"/api/pedidos/{pedido['id']}/cancelar")

        assert response.status_code == 200
        assert response.json()["mensagem"] == "Pedido cancelado com sucesso"
