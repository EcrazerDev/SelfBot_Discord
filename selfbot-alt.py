"""
Discord Selfbot en Python
Utilise discord.py-self pour les selfbots
"""

import os
import asyncio
import time
from datetime import datetime
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Configuration
TOKEN = os.getenv('TOKEN')
PREFIX = os.getenv('PREFIX', '!')

# Vérification du token
if not TOKEN:
    print('❌ ERREUR: Le token Discord n\'est pas défini dans le fichier .env')
    print('Veuillez créer un fichier .env avec votre TOKEN')
    exit(1)

# Essayer d'importer discord.py-self
try:
    import discord
    from discord.ext import commands
except ImportError:
    print('❌ discord.py n\'est pas installé')
    print('   Installez-le avec: pip install discord.py-self')
    exit(1)

# Création du client selfbot
intents = discord.Intents.default()
intents.message_content = True

# Créer le bot avec self_bot=True
bot = commands.Bot(
    command_prefix=PREFIX,
    self_bot=True,
    intents=intents,
    help_command=None  # Désactiver la commande help par défaut
)

# Variables globales
is_ready = False
command_cooldowns = {}
COOLDOWN_TIME = 1.0  # 1 seconde entre les commandes

@bot.event
async def on_ready():
    """Événement: Bot connecté"""
    global is_ready
    is_ready = True
    
    print(f'✅ Selfbot connecté en tant que {bot.user.name}#{bot.user.discriminator}')
    print(f'📝 Préfixe des commandes: {PREFIX}')
    print(f'🆔 ID: {bot.user.id}')
    print('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
    print('💡 Le bot est prêt! Tapez vos commandes dans Discord.\n')

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
    now = time.time()
    last_used = command_cooldowns.get(command_name, 0)
    if now - last_used < COOLDOWN_TIME:
        return
    command_cooldowns[command_name] = now
    
    # Exécuter les commandes
    try:
        if command_name == 'ping':
            start = time.time() * 1000
            await message.edit(content=f'🏓 Pong! Latence: {int((time.time() * 1000) - start)}ms')
        
        elif command_name == 'help':
            help_text = f"""**📋 Commandes disponibles:**

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
`{PREFIX}activity <type> <nom>` - Change l'activité (playing, streaming, listening, watching)"""
            await message.edit(content=help_text)
        
        elif command_name == 'info':
            info = f"""**📊 Informations du compte:**

**Tag:** {bot.user.name}#{bot.user.discriminator}
**ID:** {bot.user.id}
**Créé le:** {bot.user.created_at.strftime('%d/%m/%Y')}
**Bot:** {'Oui' if bot.user.bot else 'Non'}
**Serveurs:** {len(bot.guilds)}
**Utilisateurs:** {len(bot.users)}"""
            await message.edit(content=info)
        
        elif command_name == 'avatar':
            user = message.mentions[0] if message.mentions else bot.user
            avatar_url = str(user.display_avatar.url)
            await message.edit(content=f'**Avatar de {user.name}#{user.discriminator}:**\n{avatar_url}')
        
        elif command_name == 'serverinfo':
            if not message.guild:
                await message.edit(content='❌ Cette commande ne peut être utilisée que dans un serveur.')
                return
            
            guild = message.guild
            owner = guild.get_member(guild.owner_id) if guild.owner_id else None
            info = f"""**📊 Informations du serveur:**

**Nom:** {guild.name}
**ID:** {guild.id}
**Propriétaire:** {owner.name if owner else 'Inconnu'}
**Membres:** {guild.member_count}
**Salons:** {len(guild.channels)}
**Rôles:** {len(guild.roles)}
**Créé le:** {guild.created_at.strftime('%d/%m/%Y')}
**Boost:** Niveau {guild.premium_tier} ({guild.premium_subscription_count} boosts)"""
            await message.edit(content=info)
        
        elif command_name == 'userinfo':
            user = message.mentions[0] if message.mentions else bot.user
            member = message.guild.get_member(user.id) if message.guild else None
            
            info = f"""**👤 Informations de {user.name}#{user.discriminator}:**

**ID:** {user.id}
**Tag:** {user.name}#{user.discriminator}
**Bot:** {'Oui' if user.bot else 'Non'}
**Créé le:** {user.created_at.strftime('%d/%m/%Y')}"""
            
            if member and member.joined_at:
                info += f"""
**Rejoint le:** {member.joined_at.strftime('%d/%m/%Y')}
**Rôles:** {len(member.roles) - 1}"""
            
            await message.edit(content=info)
        
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
                            await asyncio.sleep(0.1)  # Délai pour éviter le rate limit
                        except:
                            pass
            except Exception:
                await message.edit(content='❌ Erreur lors de la suppression.')
        
        elif command_name == 'status':
            if not args:
                await message.edit(content=f'❌ Usage: `{PREFIX}status <online|idle|dnd|invisible>`')
                return
            
            status = args[0].lower()
            status_map = {
                'online': discord.Status.online,
                'idle': discord.Status.idle,
                'dnd': discord.Status.dnd,
                'invisible': discord.Status.invisible
            }
            
            if status not in status_map:
                await message.edit(content=f'❌ Statut invalide. Statuts disponibles: {", ".join(status_map.keys())}')
                return
            
            try:
                await bot.change_presence(status=status_map[status])
            except Exception:
                await message.edit(content='❌ Erreur lors du changement de statut.')
        
        elif command_name == 'activity':
            if len(args) < 2:
                await message.edit(content=f'❌ Usage: `{PREFIX}activity <type> <nom>`\nTypes: PLAYING, STREAMING, LISTENING, WATCHING, COMPETING')
                return
            
            activity_type = args[0].upper()
            activity_name = ' '.join(args[1:])
            
            activity_map = {
                'PLAYING': discord.ActivityType.playing,
                'STREAMING': discord.ActivityType.streaming,
                'LISTENING': discord.ActivityType.listening,
                'WATCHING': discord.ActivityType.watching,
                'COMPETING': discord.ActivityType.competing
            }
            
            if activity_type not in activity_map:
                await message.edit(content=f'❌ Usage: `{PREFIX}activity <type> <nom>`\nTypes: {", ".join(activity_map.keys())}')
                return
            
            try:
                activity = discord.Activity(type=activity_map[activity_type], name=activity_name)
                await bot.change_presence(activity=activity)
            except Exception:
                await message.edit(content='❌ Erreur lors du changement d\'activité.')
    
    except Exception as error:
        if 'Unknown Message' not in str(error):
            print(f'❌ Erreur commande {command_name}: {error}')

@bot.event
async def on_error(event, *args, **kwargs):
    """Gestion des erreurs"""
    import traceback
    print(f'❌ Erreur dans {event}:')
    traceback.print_exc()

# Connexion
print('🔄 Connexion en cours...\n')

try:
    bot.run(TOKEN, bot=False)  # bot=False pour un selfbot
except KeyboardInterrupt:
    print('\n👋 Arrêt du bot...')
except Exception as error:
    print(f'❌ ERREUR de connexion: {error}')
    if '401' in str(error) or 'Invalid' in str(error):
        print('\n💡 Le token Discord est invalide ou expiré.')
        print('   Obtenez un nouveau token depuis Discord.')
    exit(1)

