import os
import re
import socket
import subprocess
import sys
import time

import pytest

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(
        os.getenv("RUN_E2E") != "1",
        reason="Teste E2E desativado por padrao. Use RUN_E2E=1 para executar.",
    ),
]


def _porta_livre() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _esperar_servidor(base_url: str, timeout: float = 15.0) -> None:
    from urllib.request import urlopen

    limite = time.time() + timeout
    ultimo_erro = None
    while time.time() < limite:
        try:
            with urlopen(f"{base_url}/health", timeout=1) as response:
                if response.status == 200:
                    return
        except Exception as erro:
            ultimo_erro = erro
            time.sleep(0.25)
    raise RuntimeError(f"Servidor nao respondeu em {base_url}: {ultimo_erro}")


@pytest.fixture(scope="session")
def e2e_server(tmp_path_factory):
    db_path = tmp_path_factory.mktemp("e2e") / "cafeteria_e2e.db"
    port = _porta_livre()
    base_url = f"http://127.0.0.1:{port}"
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{db_path.as_posix()}"

    processo = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        cwd=os.getcwd(),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        _esperar_servidor(base_url)
        yield base_url
    finally:
        processo.terminate()
        try:
            processo.wait(timeout=5)
        except subprocess.TimeoutExpired:
            processo.kill()


def test_fluxo_completo_pedido_com_cupom_entrega_gratis(e2e_server):
    playwright = pytest.importorskip("playwright.sync_api")

    with playwright.sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=900)
        context = browser.new_context(record_video_dir="videos/")
        page = context.new_page()

        page.goto(f"{e2e_server}/painel/produtos")
        page.locator("section.form-band input[name='nome']").fill("Brownie E2E")
        page.locator("section.form-band input[name='preco']").fill("25")
        page.locator("section.form-band input[name='estoque']").fill("10")
        page.get_by_role("button", name="Cadastrar").click()
        page.get_by_text("Produto cadastrado com sucesso.").wait_for()

        page.goto(f"{e2e_server}/painel/cupons")
        page.locator("form.coupon-form input[name='codigo']").fill("E2E15")
        page.locator("form.coupon-form input[name='desconto']").fill("15")
        page.locator("form.coupon-form input[name='minimo']").fill("50")
        page.locator("form.coupon-form input[name='max_usos_por_cliente']").fill("1")
        page.get_by_role("button", name="Cadastrar").click()
        page.get_by_text("Cupom cadastrado com sucesso.").wait_for()

        page.goto(f"{e2e_server}/painel/novo-pedido")
        page.locator("input[name='cliente_id']").fill("12345678900")
        page.get_by_role("button", name="Criar Pedido").click()
        page.get_by_text("Pedido iniciado.").wait_for()

        produto = page.locator("[data-produto='brownie e2e']")
        produto.get_by_role("spinbutton").fill("3")
        produto.get_by_role("button", name="Adicionar").click()
        page.get_by_text("Item adicionado com sucesso").wait_for()

        page.get_by_label("Tipo do pedido").select_option("entrega")
        page.get_by_role("button", name="Atualizar tipo").click()
        page.get_by_text("Tipo de pedido: entrega, taxa: R$0.00").wait_for()

        page.locator("aside.summary-panel input[name='codigo']").fill("E2E15")
        page.get_by_role("button", name="Aplicar Cupom").click()
        page.get_by_text("Cupom aplicado: R$11.25 de desconto").wait_for()

        page.get_by_role("button", name="Finalizar Pedido").click()
        page.get_by_text("Pedido finalizado. Total: R$63.75").wait_for()
        page.locator(".badge.pago", has_text="pago").wait_for()
        page.get_by_text("Pagamento confirmado").wait_for()
        page.locator("button:disabled").wait_for()

        page.goto(f"{e2e_server}/painel/cupons")
        card_cupom = page.locator(".coupon-card", has_text="E2E15")
        card_cupom.get_by_text("Usos").wait_for()
        assert re.search(r"Usos\s+1\b", card_cupom.inner_text())

        browser.close()
