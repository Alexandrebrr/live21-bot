
"""
Live21 v6.0 - CORRIGE unnamed -> FOTO DE VERDADE
Bug da v5: download_media(file=bytes) perde o nome, Telegram manda como arquivo unnamed.
Fix v6: baixa para BytesIO com .name = "foto.jpg" / "video.mp4", e force_document=False
Assim volta como foto, não como arquivo.
"""
import os, json, asyncio, io
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.types import ChannelParticipantAdmin, ChannelParticipantCreator

api_id = int(os.getenv('API_ID', '0') or '0')
api_hash = os.getenv('API_HASH', '')
SESSION_STRING = os.getenv('SESSION_STRING', '')
ORIGEM = 'teamlive21'
DESTINO = 'Live21streaming'
ASSINATURA = "\n\n📢 _Informação oficial repassada para revendedores_"
PALAVRAS_BLOQUEADAS = ["salário", "demissão", "reunião interna", "senha", "link interno"]
ARQUIVO_MAPA = 'mapa_mensagens.json'

if SESSION_STRING:
    client = TelegramClient(StringSession(SESSION_STRING), api_id, api_hash)
else:
    client = TelegramClient('sessao_live21', api_id, api_hash)

if os.path.exists(ARQUIVO_MAPA):
    try:
        with open(ARQUIVO_MAPA, 'r', encoding='utf-8') as f:
            mapa_mensagens = {int(k): v for k, v in json.load(f).items()}
    except:
        mapa_mensagens = {}
else:
    mapa_mensagens = {}

def salvar_mapa():
    try:
        with open(ARQUIVO_MAPA, 'w', encoding='utf-8') as f:
            json.dump(mapa_mensagens, f)
    except Exception as e:
        print(f"Erro ao salvar mapa: {e}")

admins_cache = set()
albuns_pendentes = {}

async def e_admin(user_id):
    if user_id in admins_cache:
        return True
    try:
        p = (await client.get_participant(ORIGEM, user_id)).participant
        if isinstance(p, (ChannelParticipantAdmin, ChannelParticipantCreator)):
            admins_cache.add(user_id)
            return True
        return False
    except Exception:
        try:
            async for x in client.iter_participants(ORIGEM, filter=ChannelParticipantAdmin):
                admins_cache.add(x.id)
            async for x in client.iter_participants(ORIGEM, filter=ChannelParticipantCreator):
                admins_cache.add(x.id)
            return user_id in admins_cache
        except Exception as e2:
            print(f"Aviso admin: {e2} - liberando")
            return True

def deve_copiar(event):
    msg = event.message
    texto = getattr(msg, 'text', '') or ""
    if getattr(event, 'out', False):
        return False
    if getattr(msg, 'sticker', None):
        return False
    for palavra in PALAVRAS_BLOQUEADAS:
        if palavra.lower() in texto.lower():
            return False
    return True

def nome_arquivo(msg, idx):
    # Descobre o tipo real e dá nome com extensão certa
    try:
        if getattr(msg, 'photo', None):
            return f"foto_{msg.id}_{idx}.jpg"
        if getattr(msg, 'video', None):
            return f"video_{msg.id}_{idx}.mp4"
        if getattr(msg, 'voice', None):
            return f"audio_{msg.id}_{idx}.ogg"
        if getattr(msg, 'audio', None):
            return f"audio_{msg.id}_{idx}.mp3"
        if getattr(msg, 'document', None):
            # Tenta pegar nome original
            for attr in msg.document.attributes:
                if hasattr(attr, 'file_name') and attr.file_name:
                    return attr.file_name
            return f"arquivo_{msg.id}_{idx}.bin"
        if getattr(msg, 'gif', None):
            return f"gif_{msg.id}_{idx}.mp4"
    except:
        pass
    return f"foto_{msg.id}_{idx}.jpg"

async def baixar_com_nome(msg, idx):
    bio = io.BytesIO()
    bio.name = nome_arquivo(msg, idx)
    try:
        await client.download_media(msg, file=bio)
        bio.seek(0)
        if len(bio.getvalue()) == 0:
            return None
        return bio
    except Exception as e:
        print(f"Erro baixar {msg.id}: {e}")
        return None

async def enviar_album(grouped_id):
    await asyncio.sleep(3.0)
    eventos = albuns_pendentes.pop(grouped_id, [])
    if not eventos:
        return
    eventos = sorted(eventos, key=lambda e: e.message.id)
    primeiro = eventos[0].message
    texto = ""
    for e in eventos:
        t = e.message.text or ""
        if len(t) > len(texto):
            texto = t
    arquivos = []
    for i, e in enumerate(eventos):
        if e.message.media:
            f = await baixar_com_nome(e.message, i)
            if f:
                arquivos.append(f)
    try:
        if arquivos:
            caption = (texto + ASSINATURA) if texto else ASSINATURA
            # force_document=False = manda como FOTO, não como arquivo
            enviadas = await client.send_file(DESTINO, arquivos, caption=caption, parse_mode='md', force_document=False)
            if not isinstance(enviadas, list):
                enviadas = [enviadas]
            for i, e in enumerate(eventos):
                if i < len(enviadas):
                    mapa_mensagens[e.message.id] = enviadas[i].id
            salvar_mapa()
            print(f"✅ Álbum enviado como FOTO ({len(arquivos)} fotos)")
        else:
            enviada = await client.send_message(DESTINO, texto + ASSINATURA, parse_mode='md')
            mapa_mensagens[primeiro.id] = enviada.id
            salvar_mapa()
    except Exception as e:
        print(f"❌ Erro ao copiar álbum: {e}")

async def enviar_unico(event):
    msg = event.message
    texto = msg.text or ""
    print(f"📩 Nova mensagem de ADMIN: {texto[:80]}...")
    try:
        if msg.media:
            f = await baixar_com_nome(msg, 0)
            if f:
                enviada = await client.send_file(DESTINO, f, caption=(texto + ASSINATURA) if texto else ASSINATURA, parse_mode='md', force_document=False)
            else:
                enviada = await client.send_message(DESTINO, texto + ASSINATURA, parse_mode='md')
        else:
            enviada = await client.send_message(DESTINO, texto + ASSINATURA, parse_mode='md')
        if isinstance(enviada, list):
            mapa_mensagens[msg.id] = enviada[0].id
        else:
            mapa_mensagens[msg.id] = enviada.id
        salvar_mapa()
        print(f"✅ Enviado (origem {msg.id} -> destino {mapa_mensagens[msg.id]})")
    except Exception as e:
        print(f"❌ Erro ao copiar: {e}")

@client.on(events.NewMessage(chats=ORIGEM))
async def copiar_nova(event):
    if not deve_copiar(event):
        return
    sender_id = getattr(event, 'sender_id', None)
    if sender_id and not await e_admin(sender_id):
        print(f"⏭️ Ignorado - não é admin: {sender_id}")
        return
    msg = event.message
    grouped_id = getattr(msg, 'grouped_id', None)
    if grouped_id:
        if grouped_id not in albuns_pendentes:
            albuns_pendentes[grouped_id] = []
            asyncio.create_task(enviar_album(grouped_id))
        albuns_pendentes[grouped_id].append(event)
    else:
        await enviar_unico(event)

@client.on(events.MessageEdited(chats=ORIGEM))
async def copiar_edicao(event):
    msg = event.message
    texto = msg.text or ""
    if not deve_copiar(event):
        return
    id_destino = mapa_mensagens.get(msg.id)
    if not id_destino:
        await copiar_nova(event)
        return
    try:
        await client.edit_message(DESTINO, id_destino, texto + ASSINATURA + "\n\n✏️ _Atualizado_", parse_mode='md')
        print("✅ Atualizado!")
    except Exception as e:
        print(f"❌ Erro ao editar: {e}")
        try:
            await client.delete_messages(DESTINO, id_destino)
            await copiar_nova(event)
        except Exception as e2:
            print(f"❌ Erro reenviar: {e2}")

@client.on(events.MessageDeleted(chats=ORIGEM))
async def copiar_exclusao(event):
    for id_origem in event.deleted_ids:
        id_destino = mapa_mensagens.get(id_origem)
        if not id_destino:
            continue
        try:
            await client.delete_messages(DESTINO, id_destino)
            del mapa_mensagens[id_origem]
            salvar_mapa()
        except Exception as e:
            print(f"❌ Erro apagar {id_destino}: {e}")

print("🚀 Sistema Live21 v6.0 - FOTO DE VERDADE ligado!")
print("👀 Ouvindo: @teamlive21 (SÓ ADMINS)")
print("📤 Enviando para: @Live21streaming")
print("✏️ Monitorando EDIÇÕES")
print("🗑️ Monitorando EXCLUSÕES")
print("Aguardando...")
client.start()
client.run_until_disconnected()
