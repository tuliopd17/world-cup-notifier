# ⚽ Copa no Zap

Todo dia às **7h da manhã (horário de Brasília)** você recebe no WhatsApp um
resumão da Copa do Mundo 2026:

- 🇧🇷 **Destaque especial para a Seleção Brasileira** — resultado de ontem,
  jogo de hoje, próximo jogo com contagem regressiva e posição no grupo
- ⚽ Resultados de todos os jogos de ontem (com pênaltis e prorrogação)
- 🕐 Todos os jogos de hoje, com horário de Brasília
- 📅 Prévia dos jogos de amanhã
- 📊 Classificação completa dos 12 grupos (durante a fase de grupos)
- 🗡 Agenda do mata-mata (quando a fase de grupos acabar)

Tudo grátis: dados da [football-data.org](https://www.football-data.org) e
envio pelo [CallMeBot](https://www.callmebot.com).

## Exemplo da mensagem

```
☀️ BOM DIA! ☕
🏆 COPA DO MUNDO 2026 — Dia 3
📅 Sábado, 13 de junho

━━━━━━━━━━━━━━━
🇧🇷 SELEÇÃO BRASILEIRA 🇧🇷
━━━━━━━━━━━━━━━
🚨 HOJE TEM BRASIL! 🚨
⏰ 16h — 🇧🇷 Brasil x Croácia 🇭🇷 (Grupo C)
📍 Grupo C: Brasil em 1º lugar com 0 pts

⚽ RESULTADOS DE ONTEM
🇲🇽 México 2 x 1 Polônia 🇵🇱 (Grupo A)
...

🕐 JOGOS DE HOJE (horário de Brasília)
13h — 🇪🇸 Espanha x Marrocos 🇲🇦 (Grupo B)
...

📊 CLASSIFICAÇÃO DOS GRUPOS
Grupo A
1º 🇲🇽 México — 3 pts (1J, +1)
...
```

## Configuração (uma vez só)

### 1. Token da football-data.org

1. Cadastre-se grátis em <https://www.football-data.org/client/register>
2. Você recebe o token por e-mail. O plano gratuito cobre a Copa do Mundo.

### 2. Ativar o CallMeBot no seu WhatsApp

1. Adicione o número do bot aos seus contatos (veja o número atual em
   <https://www.callmebot.com/blog/free-api-whatsapp-messages/> — hoje é
   **+34 644 51 95 23**)
2. Envie para ele, pelo WhatsApp, a mensagem:
   `I allow callmebot to send me messages`
3. Ele responde com a sua **apikey** (um número). Guarde.

### 3. Subir o projeto para o GitHub

```bash
git init
git add .
git commit -m "Copa no Zap"
git remote add origin https://github.com/SEU_USUARIO/copa-do-mundo.git
git push -u origin main
```

### 4. Cadastrar os secrets no repositório

No GitHub: **Settings → Secrets and variables → Actions → New repository secret**

| Secret                | Valor                                  |
| --------------------- | -------------------------------------- |
| `FOOTBALL_DATA_TOKEN` | token da football-data.org             |
| `CALLMEBOT_APIKEY`    | apikey que o CallMeBot te mandou       |
| `WHATSAPP_PHONE`      | `+5535984242252`                       |

### 5. Testar

Na aba **Actions** do repositório, abra o workflow **Copa no Zap** e clique
em **Run workflow**. A mensagem deve chegar no seu WhatsApp em instantes.

## Testar localmente (sem enviar nada)

```powershell
pip install -r requirements.txt
$env:FOOTBALL_DATA_TOKEN = "seu_token"
python copa_zap.py --dry-run
```

`--dry-run` imprime a mensagem no terminal sem enviar pelo WhatsApp.

Sem token, dá para ver o formato da mensagem com dados fictícios:

```powershell
python teste_local.py
```

## Detalhes

- **Horário**: o cron roda às 09:50 UTC (06:50 em Brasília). O GitHub Actions
  costuma atrasar alguns minutos em horários cheios, então na prática a
  mensagem chega por volta das 7h. Ajuste o cron em
  [.github/workflows/copa-no-zap.yml](.github/workflows/copa-no-zap.yml) se quiser.
- **Mensagens longas**: o script divide automaticamente em partes `(1/2)`,
  `(2/2)`... quando a mensagem passa de ~1500 caracteres (limite prático do
  CallMeBot).
- **Falha na API de dados**: você recebe um aviso no WhatsApp em vez de
  silêncio, e o workflow fica vermelho para você perceber.
