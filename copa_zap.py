#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Copa no Zap — resumo diário da Copa do Mundo 2026 direto no seu WhatsApp.

Busca resultados de ontem, jogos de hoje e amanhã e a classificação dos
grupos na API football-data.org, monta uma mensagem caprichada (com
destaque especial para a Seleção Brasileira) e envia via CallMeBot.

Pensado para rodar todo dia às 7h (horário de Brasília) no GitHub Actions.

Variáveis de ambiente necessárias:
  FOOTBALL_DATA_TOKEN  token gratuito de https://www.football-data.org/client/register
  CALLMEBOT_APIKEY     chave recebida ao ativar o CallMeBot no seu WhatsApp
  WHATSAPP_PHONE       número de destino com DDI, ex: +5535984242252

Uso local (imprime a mensagem sem enviar):
  python copa_zap.py --dry-run
"""

import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import requests

API_BASE = "https://api.football-data.org/v4"
COMPETICAO = "WC"  # FIFA World Cup
BRASIL_ID = 764
TZ_BRASILIA = ZoneInfo("America/Sao_Paulo")
INICIO_COPA = datetime(2026, 6, 11).date()

# Nome usado pela API -> (bandeira, nome em português)
SELECOES = {
    "Brazil": ("🇧🇷", "Brasil"),
    "Argentina": ("🇦🇷", "Argentina"),
    "Uruguay": ("🇺🇾", "Uruguai"),
    "Paraguay": ("🇵🇾", "Paraguai"),
    "Colombia": ("🇨🇴", "Colômbia"),
    "Ecuador": ("🇪🇨", "Equador"),
    "Chile": ("🇨🇱", "Chile"),
    "Peru": ("🇵🇪", "Peru"),
    "Bolivia": ("🇧🇴", "Bolívia"),
    "Venezuela": ("🇻🇪", "Venezuela"),
    "Mexico": ("🇲🇽", "México"),
    "USA": ("🇺🇸", "Estados Unidos"),
    "United States": ("🇺🇸", "Estados Unidos"),
    "Canada": ("🇨🇦", "Canadá"),
    "Costa Rica": ("🇨🇷", "Costa Rica"),
    "Panama": ("🇵🇦", "Panamá"),
    "Honduras": ("🇭🇳", "Honduras"),
    "Jamaica": ("🇯🇲", "Jamaica"),
    "Haiti": ("🇭🇹", "Haiti"),
    "Curaçao": ("🇨🇼", "Curaçao"),
    "Curacao": ("🇨🇼", "Curaçao"),
    "France": ("🇫🇷", "França"),
    "Germany": ("🇩🇪", "Alemanha"),
    "Spain": ("🇪🇸", "Espanha"),
    "Portugal": ("🇵🇹", "Portugal"),
    "England": ("🏴󠁧󠁢󠁥󠁮󠁧󠁿", "Inglaterra"),
    "Scotland": ("🏴󠁧󠁢󠁳󠁣󠁴󠁿", "Escócia"),
    "Wales": ("🏴󠁧󠁢󠁷󠁬󠁳󠁿", "País de Gales"),
    "Netherlands": ("🇳🇱", "Holanda"),
    "Belgium": ("🇧🇪", "Bélgica"),
    "Italy": ("🇮🇹", "Itália"),
    "Croatia": ("🇭🇷", "Croácia"),
    "Switzerland": ("🇨🇭", "Suíça"),
    "Austria": ("🇦🇹", "Áustria"),
    "Denmark": ("🇩🇰", "Dinamarca"),
    "Norway": ("🇳🇴", "Noruega"),
    "Sweden": ("🇸🇪", "Suécia"),
    "Poland": ("🇵🇱", "Polônia"),
    "Ukraine": ("🇺🇦", "Ucrânia"),
    "Serbia": ("🇷🇸", "Sérvia"),
    "Bosnia-Herzegovina": ("🇧🇦", "Bósnia e Herzegovina"),
    "Bosnia and Herzegovina": ("🇧🇦", "Bósnia e Herzegovina"),
    "Slovenia": ("🇸🇮", "Eslovênia"),
    "Slovakia": ("🇸🇰", "Eslováquia"),
    "Czechia": ("🇨🇿", "Tchéquia"),
    "Czech Republic": ("🇨🇿", "Tchéquia"),
    "Romania": ("🇷🇴", "Romênia"),
    "Hungary": ("🇭🇺", "Hungria"),
    "Albania": ("🇦🇱", "Albânia"),
    "Georgia": ("🇬🇪", "Geórgia"),
    "Turkey": ("🇹🇷", "Turquia"),
    "Türkiye": ("🇹🇷", "Turquia"),
    "Greece": ("🇬🇷", "Grécia"),
    "Republic of Ireland": ("🇮🇪", "Irlanda"),
    "Ireland": ("🇮🇪", "Irlanda"),
    "Morocco": ("🇲🇦", "Marrocos"),
    "Senegal": ("🇸🇳", "Senegal"),
    "Ghana": ("🇬🇭", "Gana"),
    "Nigeria": ("🇳🇬", "Nigéria"),
    "Cameroon": ("🇨🇲", "Camarões"),
    "Ivory Coast": ("🇨🇮", "Costa do Marfim"),
    "Côte d'Ivoire": ("🇨🇮", "Costa do Marfim"),
    "Tunisia": ("🇹🇳", "Tunísia"),
    "Algeria": ("🇩🇿", "Argélia"),
    "Egypt": ("🇪🇬", "Egito"),
    "South Africa": ("🇿🇦", "África do Sul"),
    "Cape Verde": ("🇨🇻", "Cabo Verde"),
    "Cape Verde Islands": ("🇨🇻", "Cabo Verde"),
    "Cabo Verde": ("🇨🇻", "Cabo Verde"),
    "Mali": ("🇲🇱", "Mali"),
    "Burkina Faso": ("🇧🇫", "Burkina Faso"),
    "DR Congo": ("🇨🇩", "RD Congo"),
    "Congo DR": ("🇨🇩", "RD Congo"),
    "Gabon": ("🇬🇦", "Gabão"),
    "Japan": ("🇯🇵", "Japão"),
    "South Korea": ("🇰🇷", "Coreia do Sul"),
    "Korea Republic": ("🇰🇷", "Coreia do Sul"),
    "Australia": ("🇦🇺", "Austrália"),
    "Saudi Arabia": ("🇸🇦", "Arábia Saudita"),
    "Iran": ("🇮🇷", "Irã"),
    "IR Iran": ("🇮🇷", "Irã"),
    "Qatar": ("🇶🇦", "Catar"),
    "Iraq": ("🇮🇶", "Iraque"),
    "Jordan": ("🇯🇴", "Jordânia"),
    "Uzbekistan": ("🇺🇿", "Uzbequistão"),
    "United Arab Emirates": ("🇦🇪", "Emirados Árabes"),
    "UAE": ("🇦🇪", "Emirados Árabes"),
    "China": ("🇨🇳", "China"),
    "China PR": ("🇨🇳", "China"),
    "New Zealand": ("🇳🇿", "Nova Zelândia"),
    "New Caledonia": ("🇳🇨", "Nova Caledônia"),
}

FASES = {
    "GROUP_STAGE": "Fase de grupos",
    "LAST_32": "16 avos de final",
    "LAST_16": "Oitavas de final",
    "QUARTER_FINALS": "Quartas de final",
    "SEMI_FINALS": "Semifinal",
    "THIRD_PLACE": "Disputa do 3º lugar",
    "FINAL": "GRANDE FINAL",
}

FASES_CURTA = {
    "LAST_32": "16 avos",
    "LAST_16": "Oitavas",
    "QUARTER_FINALS": "Quartas",
    "SEMI_FINALS": "Semi",
    "THIRD_PLACE": "3º lugar",
    "FINAL": "🏆 FINAL",
}

DIAS_SEMANA = [
    "Segunda-feira", "Terça-feira", "Quarta-feira",
    "Quinta-feira", "Sexta-feira", "Sábado", "Domingo",
]

MESES = [
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
]

RODAPES = [
    "🤙 Bom dia e bola pra frente!",
    "☕ Café na mão e olho na bola!",
    "⚽ Hoje tem mais Copa, aproveita!",
    "🥅 Que venham os gols de hoje!",
    "📣 Rumo ao hexa! 🇧🇷",
    "🍿 Prepara a pipoca pros jogos de hoje!",
    "🔥 A Copa não para, e a gente também não!",
]


# ---------------------------------------------------------------- utilidades

def bandeira(time_api: dict) -> str:
    return SELECOES.get(time_api.get("name", ""), ("⚽", None))[0]


def nome_pt(time_api: dict) -> str:
    nome = time_api.get("name", "?")
    return SELECOES.get(nome, (None, nome))[1] or nome


def eh_brasil(time_api: dict) -> bool:
    return time_api.get("id") == BRASIL_ID or time_api.get("name") == "Brazil"


def data_hora_local(partida: dict) -> datetime:
    utc = datetime.fromisoformat(partida["utcDate"].replace("Z", "+00:00"))
    return utc.astimezone(TZ_BRASILIA)


def hora_fmt(dt: datetime) -> str:
    return f"{dt.hour}h{dt.minute:02d}" if dt.minute else f"{dt.hour}h"


def data_fmt(dt_ou_data) -> str:
    return dt_ou_data.strftime("%d/%m")


def terminou(partida: dict) -> bool:
    # A API às vezes marca jogos futuros como FINISHED com placar nulo;
    # sem placar, tratamos como ainda não jogado.
    placar = partida.get("score", {}).get("fullTime", {})
    return (
        partida.get("status") in ("FINISHED", "AWARDED")
        and placar.get("home") is not None
        and placar.get("away") is not None
    )


def letra_grupo(bruto: str) -> str:
    # Vem como "GROUP_A" nas partidas e "Group A" na classificação.
    return (bruto or "").replace("GROUP_", "").replace("Group ", "").strip()


def rotulo_fase(partida: dict) -> str:
    fase = partida.get("stage")
    if fase == "GROUP_STAGE":
        grupo = letra_grupo(partida.get("group"))
        return f"Grupo {grupo}" if grupo else "Fase de grupos"
    return FASES_CURTA.get(fase, FASES.get(fase, ""))


def confronto(partida: dict) -> str:
    casa, fora = partida["homeTeam"], partida["awayTeam"]
    return (f"{bandeira(casa)} {nome_pt(casa)} x "
            f"{nome_pt(fora)} {bandeira(fora)}")


def resultado(partida: dict) -> str:
    casa, fora = partida["homeTeam"], partida["awayTeam"]
    placar = partida["score"]["fullTime"]
    linha = (f"{bandeira(casa)} {nome_pt(casa)} {placar['home']} x "
             f"{placar['away']} {nome_pt(fora)} {bandeira(fora)}")
    duracao = partida["score"].get("duration")
    if duracao == "PENALTY_SHOOTOUT":
        pen = partida["score"].get("penalties") or {}
        linha += f" ({pen.get('home', '?')} x {pen.get('away', '?')} nos pênaltis)"
    elif duracao == "EXTRA_TIME":
        linha += " (na prorrogação)"
    return linha


# ------------------------------------------------------------------ coleta

def api_get(caminho: str, token: str) -> dict:
    resposta = requests.get(
        f"{API_BASE}{caminho}",
        headers={"X-Auth-Token": token},
        timeout=30,
    )
    resposta.raise_for_status()
    return resposta.json()


def coletar_dados(token: str) -> tuple[list, list]:
    """Retorna (todas as partidas da Copa, tabelas dos grupos)."""
    partidas = api_get(f"/competitions/{COMPETICAO}/matches", token).get("matches", [])
    try:
        bruto = api_get(f"/competitions/{COMPETICAO}/standings", token).get("standings", [])
        grupos = [g for g in bruto if g.get("type") == "TOTAL" and g.get("group")]
    except requests.RequestException:
        grupos = []  # sem classificação a mensagem ainda vale a pena
    return partidas, grupos


# --------------------------------------------------------------- mensagem

def secao_brasil(partidas: list, grupos: list, hoje) -> list[str]:
    linhas = ["━━━━━━━━━━━━━━━", "🇧🇷 *SELEÇÃO BRASILEIRA* 🇧🇷", "━━━━━━━━━━━━━━━"]
    jogos = sorted(
        (p for p in partidas if eh_brasil(p["homeTeam"]) or eh_brasil(p["awayTeam"])),
        key=lambda p: p["utcDate"],
    )

    ontem = hoje - timedelta(days=1)
    jogo_ontem = next(
        (p for p in jogos if data_hora_local(p).date() == ontem and terminou(p)), None
    )
    if jogo_ontem:
        brasil_em_casa = eh_brasil(jogo_ontem["homeTeam"])
        vencedor = jogo_ontem["score"].get("winner")
        venceu = vencedor == ("HOME_TEAM" if brasil_em_casa else "AWAY_TEAM")
        if venceu:
            linhas.append("🎉 *VITÓRIA DO BRASIL ONTEM!*")
        elif vencedor == "DRAW":
            linhas.append("😐 Empate ontem...")
        else:
            linhas.append("😢 Derrota ontem, cabeça erguida.")
        linhas.append(resultado(jogo_ontem))

    jogo_hoje = next((p for p in jogos if data_hora_local(p).date() == hoje), None)
    if jogo_hoje and not terminou(jogo_hoje):
        dt = data_hora_local(jogo_hoje)
        linhas.append("🚨 *HOJE TEM BRASIL!* 🚨")
        linhas.append(f"⏰ {hora_fmt(dt)} — {confronto(jogo_hoje)} ({rotulo_fase(jogo_hoje)})")
    elif jogo_hoje:
        linhas.append("Hoje: " + resultado(jogo_hoje))
    else:
        proximo = next(
            (p for p in jogos if data_hora_local(p).date() > hoje and not terminou(p)),
            None,
        )
        if proximo:
            dt = data_hora_local(proximo)
            dias = (dt.date() - hoje).days
            quando = "é *AMANHÃ*! 🔥" if dias == 1 else f"faltam {dias} dias"
            linhas.append(f"🔜 Próximo jogo: {confronto(proximo)}")
            linhas.append(
                f"🗓 {DIAS_SEMANA[dt.weekday()]}, {data_fmt(dt)} às {hora_fmt(dt)} — {quando}"
            )
        elif not jogo_ontem:
            linhas.append("Sem jogos do Brasil confirmados no momento.")

    for grupo in grupos:
        entrada = next(
            (e for e in grupo.get("table", []) if eh_brasil(e.get("team", {}))), None
        )
        if entrada:
            letra = letra_grupo(grupo["group"])
            linhas.append(
                f"📍 Grupo {letra}: Brasil em *{entrada['position']}º lugar* "
                f"com {entrada['points']} pts"
            )
            break

    return linhas


def secao_resultados(partidas_ontem: list) -> list[str]:
    if not partidas_ontem:
        return []
    linhas = ["⚽ *RESULTADOS DE ONTEM*"]
    for p in sorted(partidas_ontem, key=lambda x: x["utcDate"]):
        linhas.append(f"{resultado(p)} _({rotulo_fase(p)})_")
    return linhas


def secao_jogos_do_dia(partidas_hoje: list, hoje) -> list[str]:
    linhas = ["🕐 *JOGOS DE HOJE* _(horário de Brasília)_"]
    if not partidas_hoje:
        if hoje == INICIO_COPA:
            linhas.append("A bola ainda não rolou — mas a Copa começa HOJE! 🎉")
        else:
            linhas.append("Hoje não tem jogo 😴 Dia de respirar.")
        return linhas
    for p in sorted(partidas_hoje, key=lambda x: x["utcDate"]):
        dt = data_hora_local(p)
        if terminou(p):
            linhas.append(f"✅ {resultado(p)} _({rotulo_fase(p)})_")
        else:
            linhas.append(f"{hora_fmt(dt)} — {confronto(p)} _({rotulo_fase(p)})_")
    return linhas


def secao_amanha(partidas_amanha: list) -> list[str]:
    if not partidas_amanha:
        return []
    linhas = ["📅 *AMANHÃ TEM*"]
    for p in sorted(partidas_amanha, key=lambda x: x["utcDate"]):
        dt = data_hora_local(p)
        linhas.append(f"{hora_fmt(dt)} — {confronto(p)} _({rotulo_fase(p)})_")
    return linhas


def secao_classificacao(grupos: list, partidas: list, hoje) -> list[str]:
    if not grupos:
        return []
    # Depois que a fase de grupos acaba, a tabela vira ruído na mensagem.
    fase_grupos_viva = any(
        p.get("stage") == "GROUP_STAGE"
        and data_hora_local(p).date() >= hoje - timedelta(days=1)
        for p in partidas
    )
    if not fase_grupos_viva:
        return []

    linhas = ["📊 *CLASSIFICAÇÃO DOS GRUPOS*"]
    for grupo in grupos:
        letra = letra_grupo(grupo["group"])
        linhas.append(f"*Grupo {letra}*")
        for e in grupo.get("table", []):
            time_api = e.get("team", {})
            saldo = e.get("goalDifference", 0)
            linha = (
                f"{e['position']}º {bandeira(time_api)} {nome_pt(time_api)} — "
                f"{e['points']} pts ({e['playedGames']}J, {saldo:+d})"
            )
            if eh_brasil(time_api):
                linha = f"*{linha}* 👈"
            linhas.append(linha)
    return linhas


def secao_mata_mata(partidas: list, hoje) -> list[str]:
    """Próximos jogos eliminatórios (só quando a fase de grupos já era)."""
    fase_grupos_viva = any(
        p.get("stage") == "GROUP_STAGE"
        and data_hora_local(p).date() >= hoje
        for p in partidas
    )
    if fase_grupos_viva:
        return []
    futuros = sorted(
        (
            p for p in partidas
            if not terminou(p) and hoje + timedelta(days=1) < data_hora_local(p).date() <= hoje + timedelta(days=4)
        ),
        key=lambda x: x["utcDate"],
    )
    if not futuros:
        return []
    linhas = ["🗡 *PRÓXIMOS JOGOS DO MATA-MATA*"]
    for p in futuros:
        dt = data_hora_local(p)
        linhas.append(f"{data_fmt(dt)} {hora_fmt(dt)} — {confronto(p)} _({rotulo_fase(p)})_")
    return linhas


def montar_mensagem(partidas: list, grupos: list, hoje) -> str:
    ontem = hoje - timedelta(days=1)
    amanha = hoje + timedelta(days=1)

    de_ontem = [p for p in partidas if data_hora_local(p).date() == ontem and terminou(p)]
    de_hoje = [p for p in partidas if data_hora_local(p).date() == hoje]
    de_amanha = [p for p in partidas if data_hora_local(p).date() == amanha and not terminou(p)]

    dia_copa = (hoje - INICIO_COPA).days + 1
    cabecalho = [
        "☀️ *BOM DIA!* ☕",
        f"🏆 *COPA DO MUNDO 2026* — Dia {dia_copa}" if dia_copa >= 1 else "🏆 *COPA DO MUNDO 2026*",
        f"📅 {DIAS_SEMANA[hoje.weekday()]}, {hoje.day} de {MESES[hoje.month - 1]}",
    ]

    blocos = [
        cabecalho,
        secao_brasil(partidas, grupos, hoje),
        secao_resultados(de_ontem),
        secao_jogos_do_dia(de_hoje, hoje),
        secao_amanha(de_amanha),
        secao_classificacao(grupos, partidas, hoje),
        secao_mata_mata(partidas, hoje),
        [RODAPES[hoje.toordinal() % len(RODAPES)]],
    ]
    return "\n\n".join("\n".join(b) for b in blocos if b)


# ------------------------------------------------------------------- envio

def dividir_mensagem(texto: str, limite: int = 1500) -> list[str]:
    """CallMeBot engasga com textos muito longos; quebra por linha inteira."""
    partes, atual = [], ""
    for linha in texto.split("\n"):
        if atual and len(atual) + len(linha) + 1 > limite:
            partes.append(atual)
            atual = linha
        else:
            atual = f"{atual}\n{linha}" if atual else linha
    if atual:
        partes.append(atual)
    return partes


def enviar_whatsapp(texto: str, telefone: str, apikey: str) -> None:
    partes = dividir_mensagem(texto)
    total = len(partes)
    for i, parte in enumerate(partes, 1):
        if total > 1:
            parte = f"({i}/{total})\n{parte}"
        resposta = requests.get(
            "https://api.callmebot.com/whatsapp.php",
            params={"phone": telefone, "text": parte, "apikey": apikey},
            timeout=90,
        )
        resposta.raise_for_status()
        if "APIKey is invalid" in resposta.text:
            raise RuntimeError("CallMeBot recusou a APIKey — confira o secret CALLMEBOT_APIKEY.")
        print(f"Parte {i}/{total} enviada ({len(parte)} caracteres).")
        if i < total:
            time.sleep(10)  # respeita o rate limit do CallMeBot


def normalizar_telefone(bruto: str) -> str:
    numero = re.sub(r"[^\d+]", "", bruto or "")
    if numero and not numero.startswith("+"):
        numero = f"+{numero}"
    return numero


# -------------------------------------------------------------------- main

def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    dry_run = "--dry-run" in sys.argv
    token = os.environ.get("FOOTBALL_DATA_TOKEN", "")
    apikey = os.environ.get("CALLMEBOT_APIKEY", "")
    telefone = normalizar_telefone(os.environ.get("WHATSAPP_PHONE", ""))
    hoje = datetime.now(TZ_BRASILIA).date()

    if not token:
        print("ERRO: defina FOOTBALL_DATA_TOKEN.", file=sys.stderr)
        return 1
    if not dry_run and (not apikey or not telefone):
        print("ERRO: defina CALLMEBOT_APIKEY e WHATSAPP_PHONE (ou use --dry-run).", file=sys.stderr)
        return 1

    try:
        partidas, grupos = coletar_dados(token)
    except requests.RequestException as exc:
        aviso = (
            "⚠️ *Copa no Zap*\n\n"
            "Não consegui buscar os dados da Copa hoje "
            f"(erro na API: {type(exc).__name__}). Tento de novo amanhã!"
        )
        if dry_run:
            print(aviso)
        else:
            enviar_whatsapp(aviso, telefone, apikey)
        print(f"Falha na API de dados: {exc}", file=sys.stderr)
        return 1

    if not partidas:
        print("API ainda não tem partidas da Copa — nada a enviar.", file=sys.stderr)
        return 1

    mensagem = montar_mensagem(partidas, grupos, hoje)

    if dry_run:
        print(mensagem)
        print(f"\n--- dry run: {len(mensagem)} caracteres, nada foi enviado ---")
        return 0

    enviar_whatsapp(mensagem, telefone, apikey)
    print("Resumo do dia enviado com sucesso!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
