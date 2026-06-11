# -*- coding: utf-8 -*-
"""Teste rápido sem API: monta a mensagem com dados fictícios e imprime."""
import sys
from datetime import date

import copa_zap


def jogo(dia_hora, casa, fora, gols=None, stage="GROUP_STAGE", group="GROUP_C",
         winner=None, duration="REGULAR"):
    score = {"fullTime": {"home": None, "away": None}, "winner": winner,
             "duration": duration}
    status = "TIMED"
    if gols:
        score["fullTime"] = {"home": gols[0], "away": gols[1]}
        status = "FINISHED"
        if winner is None:
            score["winner"] = ("HOME_TEAM" if gols[0] > gols[1]
                               else "AWAY_TEAM" if gols[1] > gols[0] else "DRAW")
    return {
        "utcDate": dia_hora,
        "status": status,
        "stage": stage,
        "group": group if stage == "GROUP_STAGE" else None,
        "homeTeam": {"id": 99, "name": casa},
        "awayTeam": {"id": 98, "name": fora},
        "score": score,
    }


partidas = [
    # ontem (12/06)
    jogo("2026-06-12T16:00:00Z", "Mexico", "Poland", (2, 1), group="GROUP_A"),
    jogo("2026-06-12T19:00:00Z", "USA", "Japan", (1, 1), group="GROUP_B"),
    # hoje (13/06) — Brasil joga
    {**jogo("2026-06-13T19:00:00Z", "Brazil", "Croatia"),
     "homeTeam": {"id": copa_zap.BRASIL_ID, "name": "Brazil"}},
    jogo("2026-06-13T16:00:00Z", "Spain", "Morocco", group="GROUP_B"),
    # amanhã (14/06)
    jogo("2026-06-14T13:00:00Z", "France", "Senegal", group="GROUP_D"),
]

grupos = [{
    "group": "GROUP_C",
    "type": "TOTAL",
    "table": [
        {"position": 1, "team": {"id": copa_zap.BRASIL_ID, "name": "Brazil"},
         "points": 0, "playedGames": 0, "goalDifference": 0},
        {"position": 2, "team": {"id": 1, "name": "Croatia"},
         "points": 0, "playedGames": 0, "goalDifference": 0},
        {"position": 3, "team": {"id": 2, "name": "Morocco"},
         "points": 0, "playedGames": 0, "goalDifference": 0},
        {"position": 4, "team": {"id": 3, "name": "Japan"},
         "points": 0, "playedGames": 0, "goalDifference": 0},
    ],
}]

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

msg = copa_zap.montar_mensagem(partidas, grupos, date(2026, 6, 13))
print(msg)
print(f"\n--- {len(msg)} caracteres, {len(copa_zap.dividir_mensagem(msg))} parte(s) ---")
