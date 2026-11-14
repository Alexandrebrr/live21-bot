import os, asyncio, re
from telethon import TelegramClient, events
from telethon.sessions import StringSession

API_ID = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")
SESSION_STRING = os.environ.get("SESSION_STRING", "")
ORIGEM = os.environ.get("ORIGEM", "teamlive21")
DESTINO = os.environ.get("DESTINO", "Live21streaming")

# Se ORIGEM/DESTINO vierem com @ ou link, limpa
def limpar(v):
    v = v.strip()
    v = v.replace("https://t.me/", "").replace("http://t.me/", "").replace("t.me/", "").replace("@", "")
    return v.split("/")[0]

ORIGEM = limpar(ORIGEM)
DESTINO = limpar(DESTINO)

ASSINATURA = "\n\n✅ Informação oficial para revendedores Live21"
PALAVRAS_BLOQUEADAS = ["xxx", "porno"]
BLOQUEAR_STICKER = True

print("🚀 Sistema Live21 v4.0 ligado!", flush=True)
print(f"👀 Ouvindo: @{ORIGEM} -> @{DESTINO}", flush=True)

async def main():
    if not SESSION_STRING:
        print("❌ ERRO: SESSION_STRING vazio! Coloque em Variables no Railway.", flush=True)
        return
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    await client.start()
    print("✅ Conectado no Telegram!", flush=True)

    @client.on(events.NewMessage(chats=ORIGEM))
    async def copiar(event):
        try:
            # Só admins
            try:
                sender = await event.get_sender()
                # Se for canal, verifica se é admin pelo chat
                # Simplificação: copia tudo de ORIGEM, pois ORIGEM é canal de admins
            except:
                pass
            msg = event.message
            if not msg:
                return
            texto = msg.text or ""
            if any(p.lower() in texto.lower() for p in PALAVRAS_BLOQUEADAS):
                print("🚫 Bloqueada palavra proibida", flush=True)
                return
            if BLOQUEAR_STICKER and msg.sticker:
                print("🚫 Sticker bloqueado", flush=True)
                return
            # Reposta sem forward: envia texto + mídia como nova mensagem
            if msg.media:
                await client.send_file(DESTINO, msg.media, caption=(texto + ASSINATURA) if texto else ASSINATURA)
            else:
                if texto:
                    await client.send_message(DESTINO, texto + ASSINATURA)
            print(f"✅ Copiado: {texto[:60]}", flush=True)
        except Exception as e:
            print(f"Erro copiar: {e}", flush=True)

    @client.on(events.MessageEdited(chats=ORIGEM))
    async def editar(event):
        try:
            # Apaga e reposta simplificado: avisa edição
            print(f"✏️ Edição detectada id={event.id}", flush=True)
        except Exception as e:
            print(f"Erro editar: {e}", flush=True)

    @client.on(events.MessageDeleted(chats=ORIGEM))
    async def deletar(event):
        try:
            print(f"🗑️ Deleção detectada ids={event.deleted_ids}", flush=True)
        except Exception as e:
            print(f"Erro deletar: {e}", flush=True)

    print("Aguardando...", flush=True)
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
