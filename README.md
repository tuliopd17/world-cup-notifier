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

Dados grátis da [football-data.org](https://www.football-data.org).

## Arquitetura

Dois modos de envio:

| Modo | Como envia | Tamanho da mensagem | Agendamento |
| --- | --- | --- | --- |
| **Servidor próprio** (recomendado) | servidor Node + [Baileys](https://github.com/WhiskeySockets/Baileys) na sua VM, sessão do WhatsApp Web | **completa, de uma vez** | cron/systemd real, sem atraso |
| CallMeBot (fallback) | API pública gratuita | truncada em 768 (precisa particionar) | GitHub Actions (atrasa até ~2h) |

```
VM (Oracle Cloud free tier, Ubuntu, ligada 24/7)
├─ wa-server (Node + Baileys)   ← serviço systemd, mantém a sessão do WhatsApp
│    expõe POST 127.0.0.1:3000/send {text}
├─ copa_zap.py (Python)          ← systemd timer 7h BRT, monta a mensagem e envia
└─ systemd timer (horário exato, sem fila compartilhada)
```

O `copa_zap.py` escolhe o transporte sozinho: se `WA_SERVER_URL` estiver
definido, manda a mensagem **inteira** pro servidor próprio; senão, cai no
CallMeBot particionado.

## Deploy no Oracle Cloud free tier (modo recomendado)

### 1. Crie a VM

No [Oracle Cloud](https://www.oracle.com/cloud/free/) (Always Free):
**Compute → Instances → Create**. Escolha **Ubuntu 22.04+** (a opção ARM
Ampere é grátis e folgada). Guarde a chave SSH e conecte:

```bash
ssh ubuntu@SEU_IP
```

### 2. Token da football-data.org

Cadastre-se grátis em <https://www.football-data.org/client/register> — o
token chega por e-mail e o plano gratuito cobre a Copa do Mundo.

### 3. Clone e configure

```bash
sudo git clone https://github.com/tuliopd17/world-cup-notifier.git /opt/copa-do-mundo
cd /opt/copa-do-mundo
sudo cp .env.example .env
sudo nano .env        # preencha FOOTBALL_DATA_TOKEN, WHATSAPP_PHONE, WA_SERVER_TOKEN
```

No `.env`, deixe `WA_SERVER_URL=http://127.0.0.1:3000/send` e invente um
`WA_SERVER_TOKEN` qualquer (protege o endpoint local).

### 4. Rode o setup

```bash
sudo bash deploy/setup.sh
```

Ele instala Node + Python, cria o usuário de serviço, instala as
dependências e sobe os serviços systemd (`wa-server` e o `copa-zap.timer`
das 7h).

### 5. Conecte o WhatsApp (uma vez só)

```bash
sudo journalctl -u wa-server.service -f
```

Aparece um **QR code** no terminal. No celular: **WhatsApp → Aparelhos
conectados → Conectar aparelho → escaneie**. Quando logar, surge
`WhatsApp conectado`. `Ctrl+C` pra sair do log (o serviço segue rodando).

### 6. Teste o envio agora

```bash
sudo systemctl start copa-zap.service
journalctl -u copa-zap.service -n 20 --no-pager
```

A mensagem completa chega no seu zap. O disparo automático das 7h já está
agendado — confira com `systemctl list-timers copa-zap.timer`.

## Testar localmente (sem enviar nada)

```bash
pip install -r requirements.txt
export FOOTBALL_DATA_TOKEN=seu_token
python copa_zap.py --dry-run
```

`--dry-run` imprime a mensagem no terminal sem enviar. Sem token, dá pra ver
o formato com dados fictícios: `python teste_local.py`.

## Operação

- **Ver logs do envio**: `journalctl -u copa-zap.service -e`
- **Ver logs do servidor WhatsApp**: `journalctl -u wa-server.service -e`
- **Reconectar o WhatsApp** (se cair/deslogar): `sudo rm -rf /opt/copa-do-mundo/wa-server/auth && sudo systemctl restart wa-server` e escaneie o QR de novo
- **Mudar o horário**: edite `OnCalendar` em
  [deploy/copa-zap.timer](deploy/copa-zap.timer), depois
  `sudo cp deploy/copa-zap.timer /etc/systemd/system/ && sudo systemctl daemon-reload`

## Alternativa sem servidor: CallMeBot + GitHub Actions

Se não quiser manter uma VM, dá pra rodar tudo no GitHub Actions com o
CallMeBot. Limitações: mensagem truncada em 768 (o script particiona) e o
Actions atrasa até ~2h. Ative o CallMeBot mandando
`I allow callmebot to send me messages` pro número do bot
(<https://www.callmebot.com/blog/free-api-whatsapp-messages/>), pegue a
apikey, e cadastre os secrets `FOOTBALL_DATA_TOKEN`, `CALLMEBOT_APIKEY` e
`WHATSAPP_PHONE` no repositório. Deixe `WA_SERVER_URL` **vazio**. O workflow
[.github/workflows/copa-no-zap.yml](.github/workflows/copa-no-zap.yml) roda
às 08:00 UTC (~5h BRT, chegando perto das 7h após o atraso).

## Detalhes

- **Falha na API de dados**: você recebe um aviso no WhatsApp em vez de
  silêncio, e o serviço/workflow fica vermelho pra você perceber.
- **9º dígito**: o `wa-server` resolve o JID real via `onWhatsApp`, então
  funciona tanto com número com 9 quanto sem (contas antigas no Brasil).
