#!/usr/bin/env bash
# Provisiona o Copa no Zap numa VM Ubuntu (testado no Oracle Cloud free tier,
# Ubuntu 22.04/24.04 ARM ou x86). Idempotente: pode rodar de novo sem medo.
#
# Uso, na VM, como usuário com sudo:
#   git clone https://github.com/tuliopd17/world-cup-notifier.git /opt/copa-do-mundo
#   cd /opt/copa-do-mundo
#   cp .env.example .env && nano .env      # preencha os valores
#   sudo bash deploy/setup.sh
#
# Depois, conecte o WhatsApp escaneando o QR (ver instruções ao final).

set -euo pipefail

APP_DIR="/opt/copa-do-mundo"
APP_USER="copa"

if [[ $EUID -ne 0 ]]; then
  echo "Rode com sudo: sudo bash deploy/setup.sh" >&2
  exit 1
fi

if [[ ! -f "$APP_DIR/.env" ]]; then
  echo "Falta $APP_DIR/.env — copie de .env.example e preencha antes." >&2
  exit 1
fi

echo ">> Fuso horário para America/Sao_Paulo (o timer dispara às 7h locais)"
timedatectl set-timezone America/Sao_Paulo

echo ">> Garantindo swap (VMs de 1 GB, ex. E2.1.Micro, precisam ou o Baileys dá OOM)"
if ! swapon --show | grep -q '/swapfile'; then
  fallocate -l 2G /swapfile || dd if=/dev/zero of=/swapfile bs=1M count=2048
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  grep -q '^/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
  echo "   swap de 2 GB criado e ativado."
else
  echo "   swap já existe, ok."
fi

echo ">> Instalando Node.js 20, Python e venv"
if ! command -v node >/dev/null 2>&1; then
  curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
  apt-get install -y nodejs
fi
apt-get install -y python3 python3-venv python3-pip

echo ">> Criando usuário de serviço '$APP_USER'"
id -u "$APP_USER" >/dev/null 2>&1 || useradd --system --create-home --shell /usr/sbin/nologin "$APP_USER"

echo ">> Dependências Python (venv)"
python3 -m venv "$APP_DIR/.venv"
"$APP_DIR/.venv/bin/pip" install --quiet --upgrade pip
"$APP_DIR/.venv/bin/pip" install --quiet -r "$APP_DIR/requirements.txt"

echo ">> Dependências Node (Baileys)"
cd "$APP_DIR/wa-server"
sudo -u "$APP_USER" HOME="/home/$APP_USER" npm install --omit=dev --no-audit --no-fund
cd "$APP_DIR"

echo ">> Permissões"
chown -R "$APP_USER:$APP_USER" "$APP_DIR"
chmod 600 "$APP_DIR/.env"

echo ">> Instalando units do systemd"
cp "$APP_DIR/deploy/wa-server.service" /etc/systemd/system/
cp "$APP_DIR/deploy/copa-zap.service" /etc/systemd/system/
cp "$APP_DIR/deploy/copa-zap.timer" /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now wa-server.service
systemctl enable --now copa-zap.timer

echo ""
echo "============================================================"
echo " Pronto! Agora conecte o WhatsApp (uma vez só):"
echo ""
echo "   sudo journalctl -u wa-server.service -f"
echo ""
echo " Vai aparecer um QR code. No celular: WhatsApp >"
echo " Aparelhos conectados > Conectar aparelho > escaneie."
echo " Quando logar, aparece 'WhatsApp conectado'. Ctrl+C pra sair do log."
echo ""
echo " Teste o envio agora mesmo:"
echo "   sudo systemctl start copa-zap.service"
echo "   journalctl -u copa-zap.service -n 20 --no-pager"
echo ""
echo " Próximo disparo automático:"
echo "   systemctl list-timers copa-zap.timer"
echo "============================================================"
