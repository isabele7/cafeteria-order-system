# ☕ Sistema de Pedidos de Cafeteria

Projeto prático desenvolvido para a disciplina de **Verificação e Validação de Software**, focado na aplicação de boas práticas de teste e desenvolvimento.

### Conceito
O sistema simula uma aplicação interna de pedidos para cafeteria, usada por um atendente no balcão. A aplicação permite cadastrar produtos e cupons, montar pedidos, aplicar descontos, calcular taxas, registrar pagamentos e controlar o status dos pedidos.

### Stack

- **Backend:** FastAPI
- **Frontend:** Jinja2, HTMX e CSS
- **Banco de dados:** SQLite
- **ORM:** SQLAlchemy 2.0
- **Testes:** Pytest, pytest-cov

### Funcionalidades

- Cadastro e listagem de produtos.
- Controle de estoque.
- Cadastro e listagem de cupons.
- Validação de cupons por:
  - status ativo/inativo;
  - data de início;
  - data de expiração;
  - subtotal mínimo;
  - limite de uso por cliente.
- Criação de pedidos.
- Adição e remoção de itens do pedido.
- Cálculo de subtotal.
- Definição do tipo de pedido:
  - retirada;
  - entrega;
  - consumo local.
- Cálculo de taxa de entrega.
- Aplicação de cupom.
- Finalização de pedido.
- Registro de pagamento.

### Regras de Negócio

Algumas das principais regras implementadas:

- Um pedido não pode ser finalizado sem itens.
- Um produto não pode ser adicionado ao pedido se não houver estoque suficiente.
- Cupons inativos ou expirados não podem ser usados.
- Cupons podem exigir subtotal mínimo.
- O uso de cupom exige identificação do cliente (CPF), mas não é obrigatório caso contrário.
- Um cliente não pode ultrapassar o limite de uso definido para um cupom.
- Pedidos pagos ou cancelados não podem receber alterações.
- Pagamento falho não consome cupom nem incrementa o número de usos.
- O uso do cupom é incrementado somente quando o pedido é finalizado com sucesso.
