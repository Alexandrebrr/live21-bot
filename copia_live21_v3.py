
"""
SISTEMA DE CÓPIA AUTOMÁTICA - Live21 v5.0 - ÁLBUM CORRIGIDO
Origem: https://t.me/teamlive21
Destino: https://t.me/Live21streaming
v5.0 - Corrige bug do álbum:
- Álbum (2+ fotos juntas) -> manda junto como álbum, 1 legenda só
- Texto + foto -> mantém texto como legenda, não duplica
- Preserva formatação (negrito, links, emoji)
- Baixa a mídia e reenvia (sem "Encaminhado de")
- Só copia se for ADMIN
- Edita / Apaga junto
"""
import os, json, asyncio
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
# Buffer para álbum: grouped_id -> lista de eventos + task
albuns_pendentes = {}

async def e_admin(user_id):
    if user_id in admins_cache:
        return True
    try:
        participante = await client.get_participant(ORIGEM, user_id)
        p = participante.participant
        if isinstance(p, (ChannelParticipantAdmin, ChannelParticipantCreator)):
            admins_cache.add(user_id)
            return True
        return False
    except Exception:
        try:
            async for participante in client.iter_participants(ORIGEM, filter=ChannelParticipantAdmin):
                admins_cache.add(participante.id)
            async for participante in client.iter_participants(ORIGEM, filter=ChannelParticipantCreator):
                admins_cache.add(participante.id)
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

async def enviar_album(grouped_id):
    # Espera 2.5s para chegar todas as fotos do álbum
    await asyncio.sleep(2.5)
    eventos = albuns_pendentes.pop(grouped_id, [])
    if not eventos:
        return
    # Ordena pelo ID (ordem original)
    eventos = sorted(eventos, key=lambda e: e.message.id)
    primeiro = eventos[0].message
    texto = primeiro.text or ""
    # Se o texto está na última foto do álbum (Telegram às vezes coloca), pega o maior texto
    for e in eventos:
        if (e.message.text or "") and len(e.message.text) > len(texto):
            texto = e.message.text
    # Baixa todas as mídias
    arquivos = []
    for e in eventos:
        m = e.message
        if m.media:
            try:
                bio = await client.download_media(m, file=bytes)
                if bio:
                    arquivos.append(bio)
            except Exception as ex:
                print(f"Erro baixar mídia {m.id}: {ex}")
    try:
        if arquivos:
            # Manda como álbum: 1 legenda só, na primeira foto
            caption = (texto + ASSINATURA) if texto else ASSINATURA
            # Telethon: send_file com lista = álbum
            enviadas = await client.send_file(DESTINO, arquivos, caption=caption, parse_mode='md')
            if not isinstance(enviadas, list):
                enviadas = [enviadas]
            for i, e in enumerate(eventos):
                if i < len(enviadas):
                    mapa_mensagens[e.message.id] = enviadas[i].id
            salvar_mapa()
            print(f"✅ Álbum enviado ({len(arquivos)} fotos, origem {eventos[0].message.id} -> destino {enviadas[0].id})")
        else:
            enviada = await client.send_message(DESTINO, texto + ASSINATURA, parse_mode='md')
            mapa_mensagens[primeiro.id] = enviada.id
            salvar_mapa()
            print(f"✅ Texto de álbum enviado")
    except Exception as e:
        print(f"❌ Erro ao copiar álbum: {e}")

async def enviar_unico(event):
    msg = event.message
    texto = msg.text or ""
    print(f"📩 Nova mensagem de ADMIN: {texto[:80]}...")
    try:
        if msg.media:
            bio = await client.download_media(msg, file=bytes)
            if bio:
                enviada = await client.send_file(DESTINO, bio, caption=(texto + ASSINATURA) if texto else ASSINATURA, parse_mode='md')
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
        # Álbum: acumula e envia junto depois de 2.5s
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
        print(f"⚠️ Editada {msg.id} não encontrada, enviando como nova...")
        await copiar_nova(event)
        return
    print(f"✏️ Admin editou {msg.id}, atualizando...")
    try:
        novo_texto = texto + ASSINATURA + "\n\n✏️ _Atualizado_"
        await client.edit_message(DESTINO, id_destino, novo_texto, parse_mode='md')
        print("✅ Atualizado no seu canal!")
    except Exception as e:
        print(f"❌ Erro ao editar: {e}")
        try:
            await client.delete_messages(DESTINO, id_destino)
            await copiar_nova(event)
        except Exception as e2:
            print(f"❌ Erro ao reenviar: {e2}")

@client.on(events.MessageDeleted(chats=ORIGEM))
async def copiar_exclusao(event):
    ids_apagados = event.deleted_ids
    print(f"🗑️ Detectado apagamento no trabalho: {ids_apagados}")
    for id_origem in ids_apagados:
        id_destino = mapa_mensagens.get(id_origem)
        if not id_destino:
            continue
        try:
            await client.delete_messages(DESTINO, id_destino)
            print(f"   ✅ Apagado no seu canal também (destino {id_destino})")
            del mapa_mensagens[id_origem]
            salvar_mapa()
        except Exception as e:
            print(f"   ❌ Erro ao apagar {id_destino}: {e}")

print("🚀 Sistema Live21 v5.0 - ÁLBUM CORRIGIDO ligado!")
print("👀 Ouvindo: @teamlive21 (SÓ ADMINS)")
print("📤 Enviando para: @Live21streaming")
print("✏️ Monitorando EDIÇÕES")
print("🗑️ Monitorando EXCLUSÕES")
print("Aguardando...")
client.start()
client.run_until_disconnected()
