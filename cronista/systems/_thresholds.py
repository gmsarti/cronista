"""Limiares — a "física" do mundo; convertem gradação contínua em evento."""
from __future__ import annotations

MARRIAGE_THRESHOLD = 7.5       # afinidade acima disso → casam
WAR_THRESHOLD = 7.5            # tensão acima disso → guerra declarada
PEACE_THRESHOLD = 3.0          # tensão abaixo disso (ou exaustão alta) → paz
ARTIFACT_THRESHOLD = 8.0       # renome*habilidade acima disso → forja
THEFT_THRESHOLD = 6.5          # tensão + fama do artefato → tentativa de roubo
TRADE_ROUTE_THRESHOLD = 5.0    # comércio acima disso → rota comercial estabelecida
ALLIANCE_THRESHOLD = 8.0       # comércio sustentado + baixa tensão → aliança
ALLIANCE_END_THRESHOLD = 3.5   # comércio abaixo disso → aliança se desfaz

# aliases de compatibilidade — importados por tests/ (não remover sem atualizar os testes)
LIMIAR_GUERRA = WAR_THRESHOLD
LIMIAR_ROTA = TRADE_ROUTE_THRESHOLD
LIMIAR_ALIANCA = ALLIANCE_THRESHOLD
