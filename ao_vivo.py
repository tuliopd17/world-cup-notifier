#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Copa ao vivo — avisos no WhatsApp a cada início de jogo, gol e fim de jogo.

Roda como daemon (systemd). Faz polling da football-data.org com frequência
adaptativa: rápido (60s) enquanto há jogo rolando ou prestes a começar,
devagar (10 min) quando não há nada acontecendo.

⚠️ O plano gratuito da football-data.org entrega placares com ALGUM atraso
(não é tempo real puro). O gol pode chegar alguns minutos depois do lance.

Reaproveita as funções de formatação do copa_zap.py. Usa o mesmo .env
(FOOTBALL_DATA_TOKEN, WHATSAPP_PHONE, WA_SERVER_URL, WA_SERVER_TOKEN) e o
mesmo wa-server para enviar.
"""

import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone

import requests

import copa_zap as cz

TOKEN = cz.env_limpo("FOOTBALL_DATA_TOKEN")
TELEFONE = cz.normalizar_telefone(cz.env_limpo("WHATSAPP_PHONE"))
WA_URL = cz.env_limpo("WA_SERVER_URL")
WA_TOKEN = cz.env_limpo("WA_SERVER_TOKEN")

ESTADO_PATH = os.environ.get(
    "ESTADO_AO_VIVO",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "estado_ao_vivo.json"),
)
POLL_RAPIDO = int(os.environ.get("POLL_RAPIDO", "60"))
POLL_LENTO = int(os.environ.get("POLL_LENTO", "600"))

AO_VIVO = ("IN_PLAY", "PAUSED")
TERMINADO = ("FINISHED", "AWARDED")
NAO_COMECOU = ("TIMED", "SCHEDULED")


# ---------------------------------------------------------------- utilidades

def placar(m: dict) -> tuple[int, int]:
    ft = m.get("score", {}).get("fullTime", {})
    return (ft.get("home") or 0, ft.get("away") or 0)


def minuto(m: dict) -> str:
    mn = m.get("minute")
    return f" ({mn}')" if mn else ""


def brasil_joga(m: dict) -> bool:
    return cz.eh_brasil(m["homeTeam"]) or cz.eh_brasil(m["awayTeam"])


# ------------------------------------------------------------------ mensagens

def msg_inicio(m: dict) -> str:
    fase = cz.rotulo_fase(m)
    if brasil_joga(m):
        return f"🟢🇧🇷 *COMEÇOU O JOGO DO BRASIL!*\n{cz.confronto(m)}\n_{fase}_"
    return f"🟢 *Bola rolando:* {cz.confronto(m)}\n_{fase}_"


def msg_gol(m: dict, lado: str) -> str:
    marcou = m["homeTeam"] if lado == "HOME" else m["awayTeam"]
    linha = cz.resultado(m)
    fase = cz.rotulo_fase(m)
    mn = minuto(m)
    if cz.eh_brasil(marcou):
        return f"⚽🇧🇷🎉 *GOOOOOL DO BRASIL!*{mn}\n\n{linha}\n_{fase}_"
    if brasil_joga(m):
        return (f"😱 Gol do {cz.bandeira(marcou)} {cz.nome_pt(marcou)}{mn}, "
                f"torcida calada...\n\n{linha}\n_{fase}_")
    return f"⚽ *GOL!* {cz.bandeira(marcou)} {cz.nome_pt(marcou)}{mn}\n\n{linha}\n_{fase}_"


def msg_fim(m: dict) -> str:
    linha = cz.resultado(m)
    fase = cz.rotulo_fase(m)
    if brasil_joga(m):
        brasil_casa = cz.eh_brasil(m["homeTeam"])
        venc = m["score"].get("winner")
        if venc == "DRAW":
            emo = "😐 Empate."
        elif venc == ("HOME_TEAM" if brasil_casa else "AWAY_TEAM"):
            emo = "🎉 *VITÓRIA DO BRASIL!* 🇧🇷"
        else:
            emo = "😢 Derrota, cabeça erguida."
        return f"🏁 *FIM DE JOGO*\n{emo}\n{linha}\n_{fase}_"
    return f"🏁 *Fim:* {linha}\n_{fase}_"


# --------------------------------------------------------------------- envio

def enviar(texto: str) -> None:
    try:
        cz.enviar_via_servidor(texto, TELEFONE, WA_URL, WA_TOKEN)
    except Exception as exc:  # nunca derruba o daemon por falha de envio
        print(f"Falha ao enviar: {exc}", file=sys.stderr)


# ---------------------------------------------------------------- estado

def carrega_estado() -> dict | None:
    try:
        with open(ESTADO_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def salva_estado(estado: dict) -> None:
    tmp = ESTADO_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(estado, f)
    os.replace(tmp, ESTADO_PATH)


# ------------------------------------------------------------------ ciclo

def ciclo(estado: dict) -> tuple[bool, float | None]:
    """Uma passada: busca os jogos da janela, dispara avisos de transição,
    atualiza o estado. Retorna (há jogo ao vivo?, segundos até o próximo
    kickoff ou None)."""
    agora = datetime.now(timezone.utc)
    de = (agora.date() - timedelta(days=1)).isoformat()
    ate = (agora.date() + timedelta(days=1)).isoformat()
    dados = cz.api_get(f"/competitions/{cz.COMPETICAO}/matches?dateFrom={de}&dateTo={ate}", TOKEN)
    matches = dados.get("matches", [])

    algum_ao_vivo = False
    proximos = []

    for m in matches:
        mid = str(m["id"])
        st = m.get("status")
        h, a = placar(m)

        if st in AO_VIVO:
            algum_ao_vivo = True
        elif st in NAO_COMECOU:
            dt = datetime.fromisoformat(m["utcDate"].replace("Z", "+00:00"))
            delta = (dt - agora).total_seconds()
            if delta > 0:
                proximos.append(delta)

        prev = estado["matches"].get(mid)
        if prev is None:
            # Primeiro contato com este jogo: registra sem anunciar nada
            # retroativo. Se ainda não começou, o início será avisado depois.
            estado["matches"][mid] = {
                "home": h, "away": a, "status": st,
                "kickoff": st not in NAO_COMECOU,
                "fim": st in TERMINADO,
            }
            continue

        avisos = []
        if st in AO_VIVO and not prev["kickoff"]:
            avisos.append(msg_inicio(m))
            prev["kickoff"] = True
        if h > prev["home"]:
            avisos.append(msg_gol(m, "HOME"))
        if a > prev["away"]:
            avisos.append(msg_gol(m, "AWAY"))
        if st in TERMINADO and not prev["fim"]:
            avisos.append(msg_fim(m))
            prev["fim"] = True

        prev["home"], prev["away"], prev["status"] = h, a, st

        for texto in avisos:
            enviar(texto)
            time.sleep(1)

    proximo = min(proximos) if proximos else None
    return algum_ao_vivo, proximo


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    if not (TOKEN and TELEFONE and WA_URL):
        print("ERRO: ao_vivo precisa de FOOTBALL_DATA_TOKEN, WHATSAPP_PHONE e "
              "WA_SERVER_URL no .env.", file=sys.stderr)
        return 1

    estado = carrega_estado() or {"matches": {}}
    print(f"Copa ao vivo iniciado. Estado em {ESTADO_PATH}.")

    while True:
        try:
            ao_vivo, proximo = ciclo(estado)
            salva_estado(estado)
        except requests.RequestException as exc:
            print(f"Erro na API (segue tentando): {exc}", file=sys.stderr)
            ao_vivo, proximo = False, None

        if ao_vivo or (proximo is not None and proximo <= 15 * 60):
            intervalo = POLL_RAPIDO
        else:
            intervalo = POLL_LENTO
        time.sleep(intervalo)


if __name__ == "__main__":
    sys.exit(main())
