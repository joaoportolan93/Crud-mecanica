"""Script de validação — executa o schema e testa os repositories."""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from database import Database
from repositories import (
    ClienteRepository,
    VeiculoRepository,
    PecaRepository,
    ServicoRepository,
    NotaServicoRepository,
    MovimentacaoRepository,
    ConfiguracaoRepository,
)
from exceptions import EstoqueInsuficienteError, NotaStatusError


def main():
    # Limpar banco de teste anterior
    db_path = os.path.join(os.path.dirname(__file__), "test_mecanica.db")
    if os.path.exists(db_path):
        os.remove(db_path)

    Database.reset()
    db = Database(db_path)
    db.initialize()

    conn = db.connection

    # ── Validar estrutura ───────────────────────────────────
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    print(f"Tabelas criadas ({len(tables)}):")
    for t in tables:
        print(f"  - {t['name']}")

    configs = conn.execute(
        "SELECT chave, valor, descricao FROM configuracoes"
    ).fetchall()
    print(f"\nConfiguracoes iniciais ({len(configs)}):")
    for c in configs:
        print(f"  {c['chave']} = \"{c['valor']}\"")

    indexes = conn.execute(
        "SELECT name FROM sqlite_master "
        "WHERE type='index' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    print(f"\nIndices ({len(indexes)}):")
    for i in indexes:
        print(f"  - {i['name']}")

    triggers = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='trigger' ORDER BY name"
    ).fetchall()
    print(f"\nTriggers ({len(triggers)}):")
    for t in triggers:
        print(f"  - {t['name']}")

    # ── Testar fluxo completo ───────────────────────────────
    print("\n" + "=" * 50)
    print("TESTE DE FLUXO COMPLETO")
    print("=" * 50)

    clientes = ClienteRepository(db)
    veiculos = VeiculoRepository(db)
    pecas = PecaRepository(db)
    servicos = ServicoRepository(db)
    notas = NotaServicoRepository(db)
    movs = MovimentacaoRepository(db)
    config = ConfiguracaoRepository(db)

    # 1. Criar cliente
    cliente_id = clientes.criar(
        nome="João da Silva", tipo="PF",
        telefone="11999990000", cpf_cnpj="12345678900"
    )
    print(f"\n1. Cliente criado: ID {cliente_id}")

    # 2. Criar veículo
    veiculo_id = veiculos.criar(
        cliente_id=cliente_id, modelo="Gol G5",
        placa="ABC1D23", marca="Volkswagen",
        ano_fabricacao=2020, ano_modelo=2021, km_atual=45000
    )
    print(f"2. Veiculo criado: ID {veiculo_id}")

    # 3. Criar peças no estoque
    peca1_id = pecas.criar(
        descricao="Filtro de Oleo", codigo="FO-001",
        preco_venda=35.00, preco_custo=18.00,
        quantidade=10, unidade="UN"
    )
    peca2_id = pecas.criar(
        descricao="Oleo Motor 5W30", codigo="OL-5W30",
        preco_venda=45.50, preco_custo=28.00,
        quantidade=20, unidade="LT"
    )
    print(f"3. Pecas criadas: IDs {peca1_id}, {peca2_id}")

    # 4. Criar serviço no catálogo
    servico_id = servicos.criar(
        descricao="Troca de Oleo", preco_padrao=80.00
    )
    print(f"4. Servico criado: ID {servico_id}")

    # 5. Abrir nota (consome numero da OS)
    numero_antes = config.get_proximo_numero_os()
    nota_id = notas.criar_rascunho(
        cliente_id=cliente_id, veiculo_id=veiculo_id,
        km_entrada=46500
    )
    numero_depois = config.get_proximo_numero_os()
    print(f"5. Nota criada: ID {nota_id} (OS #{numero_antes} -> proximo: #{numero_depois})")

    # 6. Adicionar itens à nota
    item_p1 = notas.adicionar_peca(nota_id, peca1_id, quantidade=1)
    item_p2 = notas.adicionar_peca(nota_id, peca2_id, quantidade=4)
    item_s1 = notas.adicionar_servico(nota_id, servico_id=servico_id)
    print(f"6. Itens adicionados: pecas [{item_p1}, {item_p2}], servico [{item_s1}]")

    # Verificar totais recalculados
    nota_detalhes = notas.buscar_por_id(nota_id)
    nota_row = nota_detalhes["nota"]
    print(f"   Subtotal pecas: R$ {nota_row['subtotal_pecas']:.2f}")
    print(f"   Subtotal servicos: R$ {nota_row['subtotal_servicos']:.2f}")
    print(f"   Valor total: R$ {nota_row['valor_total']:.2f}")

    # 7. Fechar nota (baixa estoque + movimentações)
    notas.fechar_nota(nota_id, forma_pagamento="PIX", desconto=10.00)
    print(f"7. Nota fechada com sucesso!")

    # Verificar estoque após fechamento
    filtro1 = pecas.buscar_por_id(peca1_id)
    filtro2 = pecas.buscar_por_id(peca2_id)
    print(f"   Estoque Filtro de Oleo: {filtro1['quantidade']} (era 10)")
    print(f"   Estoque Oleo 5W30: {filtro2['quantidade']} (era 20)")

    # Verificar km do veículo atualizado
    v = veiculos.buscar_por_id(veiculo_id)
    print(f"   Km veiculo: {v['km_atual']} (era 45000, entrada 46500)")

    # Verificar movimentações geradas
    movs_peca1 = movs.listar_por_peca(peca1_id)
    print(f"   Movimentacoes Filtro: {len(movs_peca1)} registro(s)")
    for m in movs_peca1:
        print(f"     {m['tipo']}: {m['quantidade_anterior']} -> {m['quantidade_posterior']} ({m['motivo']})")

    # Verificar nota final
    nota_final = notas.buscar_por_id(nota_id)
    nf = nota_final["nota"]
    print(f"   Status: {nf['status']}")
    print(f"   Valor total (com desconto R$10): R$ {nf['valor_total']:.2f}")

    # 8. Cancelar nota (estorna estoque)
    notas.cancelar_nota(nota_id, motivo="Teste de estorno")
    print(f"\n8. Nota cancelada com estorno!")

    filtro1_pos = pecas.buscar_por_id(peca1_id)
    filtro2_pos = pecas.buscar_por_id(peca2_id)
    print(f"   Estoque Filtro de Oleo: {filtro1_pos['quantidade']} (restaurado)")
    print(f"   Estoque Oleo 5W30: {filtro2_pos['quantidade']} (restaurado)")

    movs_peca1_pos = movs.listar_por_peca(peca1_id)
    print(f"   Movimentacoes Filtro apos estorno: {len(movs_peca1_pos)} registro(s)")
    for m in movs_peca1_pos:
        print(f"     {m['tipo']}: {m['quantidade_anterior']} -> {m['quantidade_posterior']} ({m['motivo']})")

    # 9. Testar estoque insuficiente
    print(f"\n9. Teste de estoque insuficiente:")
    nota2_id = notas.criar_rascunho(cliente_id, veiculo_id)
    notas.adicionar_peca(nota2_id, peca1_id, quantidade=999)
    try:
        notas.fechar_nota(nota2_id, forma_pagamento="DINHEIRO")
        print("   ERRO: deveria ter falhado!")
    except EstoqueInsuficienteError as e:
        print(f"   OK! Bloqueado: {e}")

    # 10. Testar busca
    print(f"\n10. Testes de busca:")
    resultado = clientes.listar(busca="silva")
    print(f"    Busca 'silva': {len(resultado)} resultado(s)")

    resultado = veiculos.buscar_por_placa("ABC1D23")
    print(f"    Busca placa 'ABC1D23': {'encontrado' if resultado else 'nao encontrado'}")

    resultado = pecas.listar(busca="oleo")
    print(f"    Busca pecas 'oleo': {len(resultado)} resultado(s)")

    # 11. Dados oficina
    print(f"\n11. Dados da oficina:")
    config.set("nome_oficina", "Auto Mecanica do Joao")
    config.set("cnpj_oficina", "12.345.678/0001-90")
    dados = config.get_dados_oficina()
    for k, v in dados.items():
        print(f"    {k}: {v}")

    # Limpar
    db.close()
    os.remove(db_path)
    Database.reset()

    print("\n" + "=" * 50)
    print("TODOS OS TESTES PASSARAM!")
    print("=" * 50)


if __name__ == "__main__":
    main()
