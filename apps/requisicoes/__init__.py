"""App requisicoes — ciclo de vida da requisição.

Dono de Requisicao, ItemRequisicao, timeline, número público e máquina de
estados. Os services orquestram transições e podem abrir transaction.atomic
envolvendo chamadas aos services de estoque, mas nunca manipulam saldo
diretamente. Depende de accounts e estoque.
"""
