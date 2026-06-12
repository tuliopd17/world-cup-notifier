// Servidor local de envio de WhatsApp via Baileys.
//
// Mantém uma sessão do WhatsApp Web viva (autenticação persistida em disco)
// e expõe POST /send para mandar uma mensagem inteira de uma vez — sem o
// limite de 768 do CallMeBot e sem precisar particionar.
//
// Variáveis de ambiente:
//   PORT             porta HTTP (padrão 3000), escuta só em 127.0.0.1
//   AUTH_DIR         pasta da sessão do WhatsApp (padrão ./auth)
//   WA_SERVER_TOKEN  se definido, exige header X-Token igual em /send
//
// Primeira execução: imprime um QR code no terminal. Abra o WhatsApp no
// celular → Aparelhos conectados → Conectar aparelho → escaneie. A sessão
// fica salva em AUTH_DIR; reinícios não pedem QR de novo.

const path = require("path");
const express = require("express");
const pino = require("pino");
const qrcode = require("qrcode-terminal");
const {
  default: makeWASocket,
  useMultiFileAuthState,
  fetchLatestBaileysVersion,
  DisconnectReason,
} = require("@whiskeysockets/baileys");

const PORT = Number(process.env.PORT || 3000);
const AUTH_DIR = process.env.AUTH_DIR || path.join(__dirname, "auth");
const TOKEN = process.env.WA_SERVER_TOKEN || "";

let sock = null;
let pronto = false;

async function iniciar() {
  const { state, saveCreds } = await useMultiFileAuthState(AUTH_DIR);
  const { version } = await fetchLatestBaileysVersion();

  sock = makeWASocket({
    version,
    auth: state,
    logger: pino({ level: "silent" }),
    printQRInTerminal: false,
    markOnlineOnConnect: false,
  });

  sock.ev.on("creds.update", saveCreds);

  sock.ev.on("connection.update", (update) => {
    const { connection, lastDisconnect, qr } = update;

    if (qr) {
      console.log("\nEscaneie este QR no WhatsApp (Aparelhos conectados):\n");
      qrcode.generate(qr, { small: true });
    }

    if (connection === "open") {
      pronto = true;
      console.log("WhatsApp conectado. Pronto para enviar.");
    }

    if (connection === "close") {
      pronto = false;
      const code = lastDisconnect?.error?.output?.statusCode;
      const deslogado = code === DisconnectReason.loggedOut;
      console.log(`Conexão fechada (code=${code}). Reconectar=${!deslogado}`);
      if (deslogado) {
        console.log(
          "Sessão encerrada pelo WhatsApp. Apague a pasta auth/ e escaneie o QR de novo."
        );
      } else {
        setTimeout(iniciar, 3000);
      }
    }
  });
}

// Resolve o JID real do número (lida com a questão do 9º dígito no Brasil:
// o WhatsApp guarda o número sem o 9 em contas antigas).
async function resolverJid(numero) {
  const limpo = String(numero).replace(/\D/g, "");
  try {
    const achados = await sock.onWhatsApp(limpo);
    if (achados && achados[0] && achados[0].exists) {
      return achados[0].jid;
    }
  } catch (e) {
    console.error("onWhatsApp falhou, usando JID direto:", e.message);
  }
  return `${limpo}@s.whatsapp.net`;
}

const app = express();
app.use(express.json({ limit: "1mb" }));

app.get("/health", (_req, res) => {
  res.json({ pronto });
});

app.post("/send", async (req, res) => {
  if (TOKEN && req.headers["x-token"] !== TOKEN) {
    return res.status(401).json({ erro: "token invalido" });
  }
  if (!pronto) {
    return res.status(503).json({ erro: "whatsapp nao conectado" });
  }
  const { text, to } = req.body || {};
  if (!text || !to) {
    return res.status(400).json({ erro: "faltou 'text' ou 'to'" });
  }
  try {
    const jid = await resolverJid(to);
    await sock.sendMessage(jid, { text });
    console.log(`Mensagem enviada para ${jid} (${text.length} caracteres).`);
    res.json({ ok: true, jid });
  } catch (e) {
    console.error("Falha ao enviar:", e);
    res.status(500).json({ erro: String(e && e.message ? e.message : e) });
  }
});

// Só escuta em loopback: o endpoint nunca fica exposto na internet.
app.listen(PORT, "127.0.0.1", () => {
  console.log(`wa-server ouvindo em http://127.0.0.1:${PORT}`);
});

iniciar().catch((e) => {
  console.error("Erro ao iniciar Baileys:", e);
  process.exit(1);
});
