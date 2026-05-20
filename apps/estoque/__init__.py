"""App estoque — materiais e saldo.

Dono exclusivo de Material, saldo físico, saldo reservado, movimentações,
importação SCPI, divergências e saída excepcional. Nenhum outro app pode
escrever em saldo ou movimentações; toda alteração passa pelos services
públicos de estoque. Depende apenas de accounts.
"""
