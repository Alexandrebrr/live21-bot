
"""
SISTEMA DE CÓPIA AUTOMÁTICA - Live21 v3.0 FINAL
Origem: https://t.me/teamlive21
Destino: https://t.me/Live21streaming

v3.0 - SINCRONIZAÇÃO TOTAL:
- Só copia se for ADMIN do teamlive21
- Se EDITAR lá -> EDITA aqui
- Se APAGAR lá -> APAGA aqui
- Mapa salvo em arquivo, não perde se reiniciar
"""

from telethon import TelegramClient, events
from telethon.tl.types import ChannelParticipantAdmin, ChannelParticipantCreator
import json
import os

# ===== CONFIGURE AQUI =====
api_id = 12345678  # <-- TROQUE PELO SEU
api_hash = 'SEU_API_HASH_AQUI'  # <-- TROQUE PELO SEU

ORIGEM = 'teamlive21'
DESTINO = 'Live21streaming'

ASSINATURA = "\n\n📢 _Informação oficial repassada para revendedores_"
PALAVRAS_BLOQUEADAS = ["salário", "demissão", "reunião interna", "senha", "link interno"]
ARQUIVO_MAPA = 'mapa_mensagens.json'
# ===========================

client = TelegramClient('sessao_live21', api_id, api_hash)

# Carrega mapa salvo, se existir
if os.path.exists(ARQUIVO_MAPA):
    try:
        with open(ARQUIVO_MAPA, 'r', encoding='utf-8') as f:
            mapa_mensagens = json.load(f)
            # JSON salva as chaves como string, converte de volta para int
            mapa_mensagens = {int(k): v for k, v in mapa_mensagens.items()}
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

async def deve_copiar(event, verificar_admin=True):
    msg = event.message
    texto = getattr(msg, 'text', '') or ""
    if getattr(event, 'out', False):
        return False
    if getattr(msg, 'sticker', None):
        return False
    for palavra in PALAVRAS_BLOQUEADAS:
        if palavra.lower() in texto.lower():
            return False
    if verificar_admin:
        sender_id = getattr(event, 'sender_id', None)
        if not sender_id:
            return False
        if not await e_admin(sender_id):
            print(f"⏭️ Ignorado - não é admin: {sender_id}")
            return False
    return True

@client.on(events.NewMessage(chats=ORIGEM))
async def copiar_nova(event):
    if not await deve_copiar(event):
        return
    msg = event.message
    texto = msg.text or ""
    print(f"📩 Nova mensagem de ADMIN: {texto[:80]}...")
    try:
        if msg.media:
            enviada = await client.send_file(DESTINO, msg.media, caption=(texto + ASSINATURA) if texto else ASSINATURA)
        else:
            enviada = await client.send_message(DESTINO, texto + ASSINATURA)
        if isinstance(enviada, list):
            mapa_mensagens[msg.id] = enviada[0].id
        else:
            mapa_mensagens[msg.id] = enviada.id
        salvar_mapa()
        print(f"✅ Enviado (origem {msg.id} -> destino {mapa_mensagens[msg.id]})")
    except Exception as e:
        print(f"❌ Erro ao copiar: {e}")

@client.on(events.MessageEdited(chats=ORIGEM))
async def copiar_edicao(event):
    msg = event.message
    texto = msg.text or ""
    if not await deve_copiar(event):
        return
    id_destino = mapa_mensagens.get(msg.id)
    if not id_destino:
        print(f"⚠️ Editada {msg.id} não encontrada, enviando como nova...")
        await copiar_nova(event)
        return
    print(f"✏️ Admin editou {msg.id}, atualizando...")
    try:
        novo_texto = texto + ASSINATURA + "\n\n✏️ _Atualizado_"
        await client.edit_message(DESTINO, id_destino, novo_texto)
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
    # event.deleted_ids pode ter 1 ou vários IDs
    ids_apagados = event.deleted_ids
    print(f"🗑️ Detectado apagamento no trabalho: {ids_apagados}")
    for id_origem in ids_apagados:
        id_destino = mapa_mensagens.get(id_origem)
        if not id_destino:
            print(f"   - ID {id_origem} não estava no seu canal, ignorando")
            continue
        try:
            await client.delete_messages(DESTINO, id_destino)
            print(f"   ✅ Apagado no seu canal também (destino {id_destino})")
            del mapa_mensagens[id_origem]
            salvar_mapa()
        except Exception as e:
            print(f"   ❌ Erro ao apagar {id_destino}: {e}")

print("🚀 Sistema Live21 v3.0 FINAL ligado!")
print("👀 Ouvindo: @teamlive21 (SÓ ADMINS)")
print("📤 Enviando para: @Live21streaming")
print("✏️ Monitorando EDIÇÕES")
print("🗑️ Monitorando EXCLUSÕES")
print("Aguardando...")
client.start()
client.run_until_disconnected()
