import os
import json
import re
import asyncio
import discord
from datetime import datetime
from dotenv import load_dotenv
import aiohttp

# Charger les variables d'environnement
load_dotenv()

# Configuration
TOKEN = os.getenv('TOKEN')
PREFIX = os.getenv('PREFIX', '!')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')
AI_HISTORY_LIMIT = int(os.getenv('AI_HISTORY_LIMIT', '8'))

# Vérification du token
if not TOKEN:
    print('❌ ERREUR: Le token Discord n\'est pas défini dans le fichier .env')
    print('Veuillez créer un fichier .env avec votre TOKEN')
    exit(1)

# Création du client selfbot
# discord.py-self utilise discord.Client avec self_bot=True
try:
    # discord.py-self ne supporte pas Intents, on utilise Client directement
    bot = discord.Client()
except Exception as e:
    print('⚠️  Erreur lors de l\'initialisation du bot')
    print(f'   Erreur: {e}')
    print('   Assurez-vous d\'avoir installé discord.py-self')
    print('   pip install discord.py-self')
    exit(1)

# Variables pour vérifier si le bot est prêt
is_ready = False
heartbeat_received = False
ready_event_fired = False

# Système de cooldown pour éviter les requêtes excessives
command_cooldowns = {}
COOLDOWN_TIME = 1.0  # 1 seconde entre les commandes

EXPORT_DIR = 'exports'


def ensure_export_dir() -> str:
    """Crée le dossier d'export si nécessaire et renvoie son chemin."""
    os.makedirs(EXPORT_DIR, exist_ok=True)
    return EXPORT_DIR


async def export_guild_channels(guild: discord.Guild) -> str:
    """Sauvegarde les salons, catégories et rôles du serveur dans un fichier JSON et renvoie le chemin."""
    ensure_export_dir()

    channels_payload = []
    categories_count = 0
    
    # Exporter les salons et catégories
    for chan in guild.channels:
        channel_data = {
            'id': chan.id,
            'name': chan.name,
            'type': str(chan.type),
            'position': chan.position,
        }
        
        # Si c'est une catégorie, enregistrer les informations spécifiques
        if isinstance(chan, discord.CategoryChannel):
            categories_count += 1
            channel_data['is_category'] = True
            # Enregistrer les permissions de la catégorie
            overwrites = {}
            for target, overwrite in chan.overwrites.items():
                if isinstance(target, discord.Role):
                    overwrites[f'role_{target.id}'] = {
                        'allow': overwrite.pair()[0].value if overwrite.pair()[0] else 0,
                        'deny': overwrite.pair()[1].value if overwrite.pair()[1] else 0
                    }
                elif isinstance(target, discord.Member):
                    overwrites[f'member_{target.id}'] = {
                        'allow': overwrite.pair()[0].value if overwrite.pair()[0] else 0,
                        'deny': overwrite.pair()[1].value if overwrite.pair()[1] else 0
                    }
            channel_data['permissions'] = overwrites if overwrites else None
        else:
            # Pour les salons normaux
            channel_data['is_category'] = False
            channel_data['category'] = chan.category.name if chan.category else None
            channel_data['topic'] = getattr(chan, 'topic', None)
            channel_data['nsfw'] = getattr(chan, 'nsfw', False)
            
            # Enregistrer les permissions du salon
            overwrites = {}
            for target, overwrite in chan.overwrites.items():
                if isinstance(target, discord.Role):
                    overwrites[f'role_{target.id}'] = {
                        'allow': overwrite.pair()[0].value if overwrite.pair()[0] else 0,
                        'deny': overwrite.pair()[1].value if overwrite.pair()[1] else 0
                    }
                elif isinstance(target, discord.Member):
                    overwrites[f'member_{target.id}'] = {
                        'allow': overwrite.pair()[0].value if overwrite.pair()[0] else 0,
                        'deny': overwrite.pair()[1].value if overwrite.pair()[1] else 0
                    }
            channel_data['permissions'] = overwrites if overwrites else None
            
            # Informations supplémentaires pour les salons vocaux
            if isinstance(chan, discord.VoiceChannel):
                channel_data['bitrate'] = chan.bitrate
                channel_data['user_limit'] = chan.user_limit
            elif isinstance(chan, discord.StageChannel):
                channel_data['bitrate'] = chan.bitrate
                channel_data['user_limit'] = chan.user_limit
        
        channels_payload.append(channel_data)

    # Exporter les rôles (sauf @everyone et les rôles gérés par des bots)
    roles_payload = []
    for role in guild.roles:
        # Ignorer le rôle @everyone et les rôles gérés par des bots
        if role.is_default() or role.managed:
            continue
        
        role_data = {
            'id': role.id,
            'name': role.name,
            'color': role.color.value,  # Valeur hexadécimale de la couleur
            'hoist': role.hoist,  # Afficher séparément
            'mentionable': role.mentionable,
            'permissions': role.permissions.value,  # Valeur des permissions
            'position': role.position,
        }
        
        # Ajouter l'icône si disponible
        if role.icon:
            role_data['icon_url'] = role.icon.url if hasattr(role.icon, 'url') else None
        
        # Ajouter l'emoji unicode si disponible
        if role.unicode_emoji:
            role_data['unicode_emoji'] = role.unicode_emoji
        
        roles_payload.append(role_data)
    
    # Trier les rôles par position (du plus bas au plus haut pour respecter l'ordre de création)
    # Position plus élevée = rôle plus haut dans la hiérarchie
    roles_payload.sort(key=lambda x: x['position'], reverse=False)

    # Nettoyer le nom du serveur pour qu'il soit valide comme nom de fichier
    safe_guild_name = re.sub(r'[<>:"/\\|?*]', '_', guild.name)
    safe_guild_name = safe_guild_name.strip('. ')  # Enlever les points et espaces en début/fin
    if not safe_guild_name:  # Si le nom est vide après nettoyage, utiliser l'ID
        safe_guild_name = str(guild.id)
    
    filename = f'backup_{safe_guild_name}.json'
    filepath = os.path.join(EXPORT_DIR, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump({
            'guild_name': guild.name,
            'guild_id': guild.id,
            'export_date': datetime.utcnow().isoformat(),
            'categories_count': categories_count,
            'roles_count': len(roles_payload),
            'channels': channels_payload,
            'roles': roles_payload
        }, f, ensure_ascii=False, indent=2)

    return filepath


def load_channels_from_file(filename: str) -> dict:
    """Charge les salons depuis un fichier JSON."""
    if not filename.endswith('.json'):
        filename += '.json'
    
    filepath = os.path.join(EXPORT_DIR, filename)
    if not os.path.exists(filepath):
        # Essayer de trouver le fichier dans le dossier exports
        if not os.path.isabs(filepath):
            filepath = os.path.join(EXPORT_DIR, filename)
        if not os.path.exists(filepath):
            raise FileNotFoundError(f'Fichier introuvable: {filename}')
    
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
        # Compatibilité avec l'ancien format
        if isinstance(data, list):
            return {'channels': data, 'guild_name': 'Inconnu', 'categories_count': 0}
        return data


async def apply_roles_to_guild(guild: discord.Guild, roles_data: list) -> dict:
    """Applique les rôles sauvegardés sur un serveur Discord."""
    created_roles = []
    role_map = {}  # Map des anciens IDs vers les nouveaux rôles
    
    # Trier par position décroissante (du plus haut au plus bas dans la hiérarchie)
    # Dans Discord, créer les rôles du plus haut au plus bas les place automatiquement dans le bon ordre
    sorted_roles = sorted(roles_data, key=lambda x: x.get('position', 0), reverse=True)
    
    # Créer les rôles du plus haut au plus bas dans la hiérarchie
    for role_data in sorted_roles:
        try:
            # Créer le rôle avec les permissions de base
            permissions = discord.Permissions(permissions=role_data.get('permissions', 0))
            
            kwargs = {
                'name': role_data['name'],
                'permissions': permissions,
                'colour': discord.Colour(role_data.get('color', 0)),
                'hoist': role_data.get('hoist', False),
                'mentionable': role_data.get('mentionable', False),
            }
            
            # Créer le rôle
            role = await guild.create_role(**kwargs)
            
            created_roles.append(role)
            role_map[role_data.get('id')] = role
            await asyncio.sleep(0.5)  # Délai pour éviter le rate limit
            
        except discord.Forbidden:
            print(f'❌ Permissions insuffisantes pour créer le rôle {role_data.get("name", "inconnu")}')
        except Exception as e:
            print(f'❌ Erreur création rôle {role_data.get("name", "inconnu")}: {e}')
    
    return {
        'total': len(created_roles),
        'role_map': role_map
    }


def build_permission_overwrites(permissions_data: dict, guild: discord.Guild, role_map: dict = None, data: dict = None) -> dict:
    """Construit un dictionnaire d'overwrites de permissions depuis les données sauvegardées."""
    overwrites = {}
    
    if not permissions_data:
        return overwrites
    
    if not role_map:
        role_map = {}
    
    for key, perm_data in permissions_data.items():
        allow_value = perm_data.get('allow', 0)
        deny_value = perm_data.get('deny', 0)
        
        # Ignorer si les deux valeurs sont 0 (pas de permissions spécifiques)
        if allow_value == 0 and deny_value == 0:
            continue
        
        # Créer les objets Permissions depuis les valeurs
        allow_perms = discord.Permissions(permissions=allow_value)
        deny_perms = discord.Permissions(permissions=deny_value)
        
        if key.startswith('role_'):
            role_id = int(key.split('_')[1])
            # Essayer d'abord avec le role_map (rôles créés depuis le backup)
            role = role_map.get(role_id)
            
            # Si pas trouvé dans le role_map, chercher par ID sur le serveur
            if not role:
                role = guild.get_role(role_id)
            
            # Si toujours pas trouvé, essayer de trouver par nom dans les données sauvegardées
            if not role and data and 'roles' in data:
                for saved_role in data.get('roles', []):
                    if saved_role.get('id') == role_id:
                        # Chercher le rôle par nom sur le serveur
                        role = discord.utils.get(guild.roles, name=saved_role.get('name'))
                        if role:
                            break
            
            # Si toujours pas trouvé, essayer avec @everyone
            if not role:
                role = guild.default_role
            
            if role:
                overwrites[role] = discord.PermissionOverwrite.from_pair(allow_perms, deny_perms)
        elif key.startswith('member_'):
            member_id = int(key.split('_')[1])
            member = guild.get_member(member_id)
            if member:
                overwrites[member] = discord.PermissionOverwrite.from_pair(allow_perms, deny_perms)
    
    return overwrites


async def apply_channels_to_guild(guild: discord.Guild, data: dict, role_map: dict = None) -> dict:
    """Applique les salons sauvegardés sur un serveur Discord."""
    created_channels = []
    category_map = {}  # Map des noms de catégories vers les objets CategoryChannel
    
    # Extraire les channels du format
    channels_data = data.get('channels', data) if isinstance(data, dict) else data
    
    # Trier par position pour respecter l'ordre
    sorted_channels = sorted(channels_data, key=lambda x: x.get('position', 0))
    
    # Créer les catégories d'abord
    categories_data = [ch for ch in sorted_channels if ch.get('is_category') or ch.get('type') == 'ChannelType.category']
    for cat_data in categories_data:
        try:
            category = await guild.create_category(
                name=cat_data['name'],
                position=cat_data.get('position', 0)
            )
            
            # Appliquer les permissions de la catégorie si disponibles
            if cat_data.get('permissions'):
                overwrites = build_permission_overwrites(cat_data.get('permissions'), guild, role_map, data)
                if overwrites:
                    try:
                        await category.edit(overwrites=overwrites)
                        await asyncio.sleep(0.3)  # Petit délai après l'application des permissions
                    except discord.Forbidden:
                        print(f'⚠️  Permissions insuffisantes pour appliquer les overwrites à la catégorie {cat_data["name"]}')
                    except Exception as e:
                        print(f'⚠️  Impossible d\'appliquer les permissions à la catégorie {cat_data["name"]}: {e}')
            
            category_map[cat_data['name']] = category
            created_channels.append(category)
            await asyncio.sleep(0.5)  # Délai pour éviter le rate limit
        except Exception as e:
            print(f'❌ Erreur création catégorie {cat_data["name"]}: {e}')
    
    # Créer les salons
    non_category_channels = [ch for ch in sorted_channels if not ch.get('is_category') and ch.get('type') != 'ChannelType.category']
    
    for ch_data in non_category_channels:
        try:
            # Déterminer le type de salon
            channel_type_str = ch_data.get('type', 'ChannelType.text')
            
            # Mapper les types de salons
            if 'text' in channel_type_str.lower():
                channel_type = discord.ChannelType.text
            elif 'voice' in channel_type_str.lower():
                channel_type = discord.ChannelType.voice
            elif 'forum' in channel_type_str.lower():
                channel_type = discord.ChannelType.forum
            elif 'stage' in channel_type_str.lower():
                channel_type = discord.ChannelType.stage_voice
            elif 'news' in channel_type_str.lower():
                channel_type = discord.ChannelType.news
            else:
                channel_type = discord.ChannelType.text  # Par défaut
            
            # Récupérer la catégorie si elle existe
            category = None
            if ch_data.get('category'):
                category = category_map.get(ch_data['category'])
            
            # Créer le salon
            kwargs = {
                'name': ch_data['name'],
                'category': category,
                'position': ch_data.get('position', 0),
                'nsfw': ch_data.get('nsfw', False)
            }
            
            if channel_type == discord.ChannelType.text:
                channel = await guild.create_text_channel(**kwargs)
                if ch_data.get('topic'):
                    try:
                        await channel.edit(topic=ch_data['topic'])
                    except:
                        pass
            elif channel_type == discord.ChannelType.voice:
                # Ajouter bitrate et user_limit pour les salons vocaux
                if 'bitrate' in ch_data:
                    kwargs['bitrate'] = ch_data['bitrate']
                if 'user_limit' in ch_data:
                    kwargs['user_limit'] = ch_data['user_limit']
                channel = await guild.create_voice_channel(**kwargs)
            elif channel_type == discord.ChannelType.forum:
                channel = await guild.create_forum_channel(**kwargs)
            elif channel_type == discord.ChannelType.stage_voice:
                # Ajouter bitrate et user_limit pour les salons stage
                if 'bitrate' in ch_data:
                    kwargs['bitrate'] = ch_data['bitrate']
                if 'user_limit' in ch_data:
                    kwargs['user_limit'] = ch_data['user_limit']
                channel = await guild.create_stage_channel(**kwargs)
            elif channel_type == discord.ChannelType.news:
                channel = await guild.create_news_channel(**kwargs)
            else:
                channel = await guild.create_text_channel(**kwargs)
            
            # Appliquer les permissions du salon si disponibles
            if ch_data.get('permissions'):
                overwrites = build_permission_overwrites(ch_data.get('permissions'), guild, role_map, data)
                if overwrites:
                    try:
                        await channel.edit(overwrites=overwrites)
                        await asyncio.sleep(0.3)  # Petit délai après l'application des permissions
                    except discord.Forbidden:
                        print(f'⚠️  Permissions insuffisantes pour appliquer les overwrites au salon {ch_data.get("name", "inconnu")}')
                    except Exception as e:
                        print(f'⚠️  Impossible d\'appliquer les permissions au salon {ch_data.get("name", "inconnu")}: {e}')
            
            created_channels.append(channel)
            await asyncio.sleep(0.5)  # Délai pour éviter le rate limit
            
        except discord.Forbidden:
            print(f'❌ Permissions insuffisantes pour créer le salon {ch_data.get("name", "inconnu")}')
        except Exception as e:
            print(f'❌ Erreur création salon {ch_data.get("name", "inconnu")}: {e}')
    
    return {
        'total': len(created_channels),
        'categories': len(categories_data),
        'channels': len(created_channels) - len(categories_data)
    }


async def call_openai_chat(prompt: str) -> str:
    """Interroge l'API d'OpenAI et renvoie la réponse textuelle."""
    if not OPENAI_API_KEY:
        raise RuntimeError('OPENAI_API_KEY manquant dans le fichier .env')

    payload = {
        'model': OPENAI_MODEL,
        'messages': [
            {
                'role': 'system',
                'content': 'Tu es un assistant francophone pour Discord. Réponds de façon concise.'
            },
            {
                'role': 'user',
                'content': prompt
            }
        ],
        'temperature': 0.7,
        'max_tokens': 400
    }

    headers = {
        'Authorization': f'Bearer {OPENAI_API_KEY}',
        'Content-Type': 'application/json'
    }

    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60)) as session:
        async with session.post('https://api.openai.com/v1/chat/completions', json=payload, headers=headers) as resp:
            data = await resp.json()
            if resp.status != 200:
                error_message = data.get('error', {}).get('message', 'Erreur inconnue')
                raise RuntimeError(f'API OpenAI: {error_message}')
            choices = data.get('choices')
            if not choices:
                raise RuntimeError('Réponse vide de la part de l’IA')
            return choices[0]['message']['content'].strip()


async def build_conversation_context(channel, limit: int, ignore_id: int = None) -> str:
    """Prépare un résumé textuel des derniers messages du salon."""
    messages = []
    async for msg in channel.history(limit=limit):
        if ignore_id and msg.id == ignore_id:
            continue
        if msg.content:
            author = 'Moi' if msg.author == bot.user else msg.author.display_name
            messages.append(f'{author}: {msg.content}')
    messages.reverse()
    return '\n'.join(messages) if messages else 'Aucun contexte disponible.'

def trigger_ready_event():
    """Force le déclenchement de l'événement ready"""
    global is_ready, ready_event_fired
    
    if ready_event_fired:
        return
    
    if bot.user and not is_ready:
        ready_event_fired = True
        is_ready = True
        
        try:
            # Émettre l'événement ready manuellement
            asyncio.create_task(on_ready_manual())
            print(f'✅ Selfbot connecté en tant que {bot.user.name}#{bot.user.discriminator}')
            print(f'📝 Préfixe des commandes: {PREFIX}')
            print(f'🆔 ID: {bot.user.id}')
            print('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
            print('💡 Le bot est prêt! Tapez vos commandes dans Discord.\n')
        except Exception as error:
            print(f'❌ Erreur lors du déclenchement de ready: {error}')

async def on_ready_manual():
    """Fonction appelée manuellement quand ready est déclenché"""
    pass

@bot.event
async def on_ready():
    """Événement: Bot connecté"""
    global is_ready, ready_event_fired
    
    ready_event_fired = True
    is_ready = True
    
    try:
        print(f'✅ Selfbot connecté en tant que {bot.user.name}#{bot.user.discriminator}')
        print(f'📝 Préfixe des commandes: {PREFIX}')
        print(f'🆔 ID: {bot.user.id}')
        print('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
        print('💡 Le bot est prêt! Tapez vos commandes dans Discord.\n')
    except Exception as error:
        print(f'❌ Erreur lors de l\'initialisation: {error}')

@bot.event
async def on_message(message):
    """Événement: Message reçu"""
    global is_ready
    
    # Vérifier que le bot est prêt
    if not is_ready or not bot.user:
        return
    
    # Ignorer les messages du bot lui-même
    if message.author.id != bot.user.id:
        return
    
    # Ignorer les messages qui ne commencent pas par le préfixe
    if not message.content.startswith(PREFIX):
        return
    
    # Parser la commande
    args = message.content[len(PREFIX):].strip().split()
    if not args:
        return
    
    command_name = args[0].lower()
    args = args[1:] if len(args) > 1 else []
    
    # Vérifier le cooldown
    import time
    now = time.time()
    last_used = command_cooldowns.get(command_name, 0)
    if now - last_used < COOLDOWN_TIME:
        return
    command_cooldowns[command_name] = now
    
    # Exécuter la commande
    try:
        if command_name == 'ping':
            start = time.time() * 1000
            await message.edit(content=f'🏓 Pong! Latence: {int((time.time() * 1000) - start)}ms')
        
        elif command_name == 'help':
            help_text = f"""
**📋 Commandes disponibles:**

`{PREFIX}ping` - Affiche la latence du bot
`{PREFIX}help` - Affiche ce message d'aide
`{PREFIX}info` - Affiche les informations du compte
`{PREFIX}avatar [@user]` - Affiche l'avatar d'un utilisateur
`{PREFIX}serverinfo` - Affiche les informations du serveur
`{PREFIX}userinfo [@user]` - Affiche les informations d'un utilisateur
`{PREFIX}say <message>` - Répète un message
`{PREFIX}embed <titre> | <description>` - Crée un embed
`{PREFIX}purge <nombre>` - Supprime vos propres messages
`{PREFIX}status <type>` - Change le statut (online, idle, dnd, invisible)
`{PREFIX}activity <type> <nom>` - Change l'activité (playing, streaming, listening, watching)
`{PREFIX}kick_vocal @user <nombre>` - Expulse un utilisateur d'un canal vocal plusieurs fois
`{PREFIX}ai [question]` - Génère une réponse IA en utilisant le contexte du salon
`{PREFIX}save_backup` - Sauvegarde les salons, catégories et rôles du serveur dans un fichier JSON
`{PREFIX}load_backup [fichier]` - Applique un backup complet (rôles, salons, catégories) sur ce serveur
            """.strip()
            await message.edit(content=help_text)
        
        elif command_name == 'info':
            info = f"""
**📊 Informations du compte:**

**Tag:** {bot.user.name}#{bot.user.discriminator}
**ID:** {bot.user.id}
**Créé le:** {bot.user.created_at.strftime('%d/%m/%Y')}
**Bot:** {'Oui' if bot.user.bot else 'Non'}
**Serveurs:** {len(bot.guilds)}
**Utilisateurs:** {len(bot.users)}
            """.strip()
            await message.edit(content=info)
        
        elif command_name == 'avatar':
            user = message.mentions[0] if message.mentions else bot.user
            avatar_url = user.display_avatar.url
            await message.edit(content=f'**Avatar de {user.name}#{user.discriminator}:**\n{avatar_url}')
        
        elif command_name == 'serverinfo':
            if not message.guild:
                await message.edit(content='❌ Cette commande ne peut être utilisée que dans un serveur.')
                return
            
            guild = message.guild
            owner = guild.get_member(guild.owner_id)
            info = f"""
**📊 Informations du serveur:**

**Nom:** {guild.name}
**ID:** {guild.id}
**Propriétaire:** {owner.name if owner else 'Inconnu'}
**Membres:** {guild.member_count}
**Salons:** {len(guild.channels)}
**Rôles:** {len(guild.roles)}
**Créé le:** {guild.created_at.strftime('%d/%m/%Y')}
**Boost:** Niveau {guild.premium_tier} ({guild.premium_subscription_count} boosts)
            """.strip()
            await message.edit(content=info)
        
        elif command_name == 'userinfo':
            user = message.mentions[0] if message.mentions else bot.user
            member = message.guild.get_member(user.id) if message.guild else None
            
            info = f"""
**👤 Informations de {user.name}#{user.discriminator}:**

**ID:** {user.id}
**Tag:** {user.name}#{user.discriminator}
**Bot:** {'Oui' if user.bot else 'Non'}
**Créé le:** {user.created_at.strftime('%d/%m/%Y')}
            """
            
            if member:
                info += f"""
**Rejoint le:** {member.joined_at.strftime('%d/%m/%Y') if member.joined_at else 'Inconnu'}
**Rôles:** {len(member.roles) - 1}
**Permissions:** {len([p for p in member.guild_permissions if p[1]])}
                """
            
            await message.edit(content=info.strip())
        
        elif command_name == 'say':
            text = ' '.join(args)
            if not text:
                await message.edit(content=f'❌ Usage: `{PREFIX}say <message>`')
                return
            await message.edit(content=text)
        
        elif command_name == 'embed':
            text = ' '.join(args)
            if '|' not in text:
                await message.edit(content=f'❌ Usage: `{PREFIX}embed <titre> | <description>`')
                return
            
            title, description = text.split('|', 1)
            embed = discord.Embed(
                title=title.strip(),
                description=description.strip(),
                color=0x5865F2,
                timestamp=datetime.utcnow()
            )
            await message.edit(content=None, embed=embed)
        
        elif command_name == 'purge':
            if not args:
                await message.edit(content='❌ Veuillez spécifier un nombre entre 1 et 100.')
                return
            
            try:
                amount = int(args[0])
                if amount < 1 or amount > 100:
                    await message.edit(content='❌ Veuillez spécifier un nombre entre 1 et 100.')
                    return
            except ValueError:
                await message.edit(content='❌ Veuillez spécifier un nombre valide.')
                return
            
            if not message.channel:
                await message.edit(content='❌ Cette commande ne peut être utilisée que dans un salon.')
                return
            
            deleted = 0
            fetch_limit = min(amount + 10, 100)
            
            try:
                async for msg in message.channel.history(limit=fetch_limit):
                    if msg.author.id == bot.user.id and deleted < amount:
                        try:
                            await msg.delete()
                            deleted += 1
                            await asyncio.sleep(0.1)  # Petit délai pour éviter le rate limit
                        except:
                            pass
            except Exception as e:
                await message.edit(content='❌ Erreur lors de la suppression.')
        
        elif command_name == 'ai':
            user_prompt = ' '.join(args).strip()
            await message.edit(content='🤖 Génération de la réponse IA en cours...')
            try:
                context_text = await build_conversation_context(message.channel, AI_HISTORY_LIMIT, ignore_id=message.id)
                prompt_parts = [
                    'Contexte récent de la conversation:',
                    context_text,
                    '',
                    'Instruction:',
                ]
                if user_prompt:
                    prompt_parts.append(user_prompt)
                else:
                    prompt_parts.append('Réponds naturellement au dernier message du contexte.')
                prompt = '\n'.join(prompt_parts)
                ai_reply = await call_openai_chat(prompt)
                if len(ai_reply) > 1900:
                    ai_reply = ai_reply[:1900] + '…'
                await message.edit(content=ai_reply)
            except RuntimeError as api_error:
                await message.edit(content=f'❌ Impossible d’utiliser l’IA: {api_error}')
            except Exception as e:
                await message.edit(content='❌ Erreur inattendue lors de l’appel à l’IA.')
                print(f'❌ Erreur commande ai: {e}')

        elif command_name == 'status':
            if not args:
                await message.edit(content='❌ Usage: `!status <online|idle|dnd|invisible>`')
                return
            
            status = args[0].lower()
            valid_statuses = ['online', 'idle', 'dnd', 'invisible']
            
            if status not in valid_statuses:
                await message.edit(content=f'❌ Statut invalide. Statuts disponibles: {", ".join(valid_statuses)}')
                return
            
            try:
                status_map = {
                    'online': discord.Status.online,
                    'idle': discord.Status.idle,
                    'dnd': discord.Status.dnd,
                    'invisible': discord.Status.invisible
                }
                await bot.change_presence(status=status_map[status])
            except Exception as e:
                await message.edit(content='❌ Erreur lors du changement de statut.')
        
        elif command_name == 'activity':
            if len(args) < 2:
                await message.edit(content=f'❌ Usage: `{PREFIX}activity <type> <nom>`\nTypes: PLAYING, STREAMING, LISTENING, WATCHING, COMPETING')
                return
            
            activity_type = args[0].upper()
            activity_name = ' '.join(args[1:])
            
            valid_types = ['PLAYING', 'STREAMING', 'LISTENING', 'WATCHING', 'COMPETING']
            
            if activity_type not in valid_types:
                await message.edit(content=f'❌ Usage: `{PREFIX}activity <type> <nom>`\nTypes: {", ".join(valid_types)}')
                return
            
            try:
                activity_map = {
                    'PLAYING': discord.ActivityType.playing,
                    'STREAMING': discord.ActivityType.streaming,
                    'LISTENING': discord.ActivityType.listening,
                    'WATCHING': discord.ActivityType.watching,
                    'COMPETING': discord.ActivityType.competing
                }
                activity = discord.Activity(type=activity_map[activity_type], name=activity_name)
                await bot.change_presence(activity=activity)
            except Exception as e:
                await message.edit(content='❌ Erreur lors du changement d\'activité.')
        
        elif command_name == 'kick_vocal':
            # Commande pour kicker quelqu'un d'un canal vocal plusieurs fois
            if not message.guild:
                await message.edit(content='❌ Cette commande ne peut être utilisée que dans un serveur.')
                return
            
            if not message.mentions:
                await message.edit(content=f'❌ Usage: `{PREFIX}kick_vocal @utilisateur <nombre>`\nVous devez mentionner un utilisateur et spécifier le nombre de fois.')
                return
            
            # Récupérer le nombre de fois (par défaut 1)
            try:
                if len(args) > 0 and args[0].isdigit():
                    # Si le premier argument après la mention est un nombre
                    kick_count = int(args[0])
                elif len(args) > 1 and args[1].isdigit():
                    # Si le nombre est après la mention
                    kick_count = int(args[1])
                else:
                    kick_count = 1
                
                if kick_count < 1:
                    kick_count = 1
                elif kick_count > 20:  # Limiter à 20 pour éviter les abus
                    kick_count = 20
            except (ValueError, IndexError):
                kick_count = 1
            
            target_user = message.mentions[0]
            member = message.guild.get_member(target_user.id)
            
            if not member:
                await message.edit(content='❌ Utilisateur introuvable dans ce serveur.')
                return
            
            # Vérifier si l'utilisateur est dans un canal vocal
            if not member.voice or not member.voice.channel:
                await message.edit(content=f'❌ {member.display_name} n\'est pas dans un canal vocal.')
                return
            
            try:
                success_count = 0
                # Boucle pour kicker plusieurs fois
                for i in range(kick_count):
                    try:
                        # Déconnecter l'utilisateur du canal vocal
                        await member.edit(voice_channel=None)
                        success_count += 1
                        # Petit délai entre chaque kick pour éviter le rate limit
                        if i < kick_count - 1:  # Pas de délai après le dernier
                            await asyncio.sleep(0.5)
                    except discord.Forbidden:
                        break  # Arrêter si on n'a plus les permissions
                    except Exception:
                        pass  # Continuer même en cas d'erreur
                
                if success_count > 0:
                    await message.edit(content=f'✅ {member.display_name} a été expulsé {success_count} fois du canal vocal.')
                else:
                    await message.edit(content='❌ Impossible d\'expulser cet utilisateur.')
            except discord.Forbidden:
                await message.edit(content='❌ Permissions insuffisantes pour expulser cet utilisateur.')
            except Exception as e:
                await message.edit(content=f'❌ Erreur lors de l\'expulsion: {str(e)}')
        
        elif command_name == 'save_backup':
            if not message.guild:
                await message.edit(content='❌ Cette commande ne peut être utilisée que dans un serveur.')
                return

            try:
                await message.edit(content='💾 Sauvegarde des salons, catégories et rôles en cours...')
                export_path = await export_guild_channels(message.guild)
                
                # Lire le fichier pour obtenir les statistiques
                try:
                    with open(export_path, 'r', encoding='utf-8') as f:
                        saved_data = json.load(f)
                        categories_count = saved_data.get('categories_count', 0)
                        channels_count = len(saved_data.get('channels', [])) - categories_count
                        roles_count = saved_data.get('roles_count', 0)
                        total = len(saved_data.get('channels', []))
                        await message.edit(content=f'✅ **Sauvegarde terminée!**\n📊 {total} éléments sauvegardés ({categories_count} catégories, {channels_count} salons, {roles_count} rôles)\n💾 Fichier: `{export_path}`')
                except:
                    await message.edit(content=f'✅ {len(message.guild.channels)} éléments sauvegardés dans `{export_path}`.')
            except Exception as e:
                await message.edit(content='❌ Erreur lors de la sauvegarde.')
                print(f'❌ Erreur sauvegarde: {e}')
        
        elif command_name == 'load_backup':
            if not message.guild:
                await message.edit(content='❌ Cette commande ne peut être utilisée que dans un serveur.')
                return
            
            if not args:
                # Lister les fichiers disponibles
                try:
                    ensure_export_dir()
                    # Chercher les fichiers backup_ et channels_ pour compatibilité
                    files = [f for f in os.listdir(EXPORT_DIR) if (f.startswith('backup_') or f.startswith('channels_')) and f.endswith('.json')]
                    if not files:
                        await message.edit(content='❌ Aucun fichier de sauvegarde trouvé dans le dossier `exports/`.')
                        return
                    
                    files_list = '\n'.join([f'• `{f}`' for f in sorted(files, reverse=True)[:10]])
                    await message.edit(content=f'**📁 Fichiers disponibles:**\n{files_list}\n\n💡 Usage: `{PREFIX}load_backup <nom_fichier>`')
                except Exception as e:
                    await message.edit(content='❌ Erreur lors de la lecture des fichiers.')
                    print(f'❌ Erreur listage fichiers: {e}')
                return
            
            filename = ' '.join(args)
            try:
                await message.edit(content='📥 Chargement du fichier...')
                data = load_channels_from_file(filename)
                
                channels_data = data.get('channels', data) if isinstance(data, dict) else data
                roles_data = data.get('roles', []) if isinstance(data, dict) else []
                total_count = len(channels_data)
                categories_count = len([ch for ch in channels_data if ch.get('is_category') or ch.get('type') == 'ChannelType.category'])
                roles_count = len(roles_data)
                
                guild_name = data.get('guild_name', 'Inconnu') if isinstance(data, dict) else 'Inconnu'
                
                # Créer les rôles d'abord si disponibles
                role_map = {}
                roles_result = None
                if roles_data:
                    await message.edit(content=f'📥 Fichier chargé: **{guild_name}**\n👥 Création de {roles_count} rôles en cours...')
                    roles_result = await apply_roles_to_guild(message.guild, roles_data)
                    role_map = roles_result.get('role_map', {})
                    await asyncio.sleep(1)  # Petit délai entre les rôles et les salons
                
                await message.edit(content=f'📥 Fichier chargé: **{guild_name}**\n🔨 Création de {total_count} éléments ({categories_count} catégories) en cours... (cela peut prendre du temps)')
                result = await apply_channels_to_guild(message.guild, data, role_map)
                
                roles_msg = f'\n👥 Rôles: {roles_result["total"]}' if roles_result else ''
                await message.edit(content=f'✅ **Backup restauré avec succès!**\n📊 Salons: {result["total"]} ({result["categories"]} catégories, {result["channels"]} salons){roles_msg}')
            except FileNotFoundError as e:
                await message.edit(content=f'❌ Fichier introuvable: `{filename}`\n💡 Utilisez `{PREFIX}load_backup` pour voir les fichiers disponibles.')
            except json.JSONDecodeError:
                await message.edit(content='❌ Fichier JSON invalide.')
            except discord.Forbidden:
                await message.edit(content='❌ Permissions insuffisantes pour créer des salons.')
            except Exception as e:
                await message.edit(content=f'❌ Erreur lors de l\'application des salons: {str(e)}')
                print(f'❌ Erreur application salons: {e}')
    
    except Exception as error:
        # Log seulement les erreurs importantes
        if 'Unknown Message' not in str(error):
            print(f'❌ Erreur commande {command_name}: {error}')

@bot.event
async def on_error(event, *args, **kwargs):
    """Gestion des erreurs"""
    import traceback
    print(f'❌ Erreur dans {event}:')
    traceback.print_exc()

# Gestion des erreurs de connexion
@bot.event
async def on_connect():
    """Événement: Connexion établie"""
    print('🔄 Connexion établie...')

@bot.event
async def on_disconnect():
    """Événement: Déconnexion"""
    print('⚠️  Déconnecté de Discord')

# Connexion au compte Discord
print('🔄 Connexion en cours...\n')

try:
    bot.run(TOKEN)  # discord.py-self gère automatiquement les selfbots
except Exception as error:
    print(f'❌ ERREUR de connexion: {error}')
    if '401' in str(error) or 'Invalid' in str(error):
        print('\n💡 Le token Discord est invalide ou expiré.')
        print('   Obtenez un nouveau token depuis Discord.')
    exit(1)

