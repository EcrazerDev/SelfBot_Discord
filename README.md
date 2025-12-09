# Discord Selfbot en Python

⚠️ **AVERTISSEMENT IMPORTANT** ⚠️

**Les selfbots sont STRICTEMENT INTERDITS par Discord et violent les Conditions d'Utilisation (ToS).**

L'utilisation de ce selfbot peut entraîner:
- La suspension permanente de votre compte Discord
- Le bannissement de votre compte
- Des conséquences légales dans certains cas

**Utilisez ce code uniquement à des fins éducatives ou sur un serveur de test privé.**

## 📋 Prérequis

- Python 3.8 ou supérieur
- Un compte Discord
- Votre token Discord (voir instructions ci-dessous)

## 🚀 Installation

1. **Installez les dépendances:**
```bash
pip install -r requirements-python.txt
```

Ou manuellement:
```bash
pip install discord.py-self python-dotenv
```

**Note importante:** `discord.py-self` est un fork de `discord.py` pour les selfbots. Si vous avez des problèmes d'installation, vous pouvez essayer:
```bash
pip install git+https://github.com/dolfies/discord.py-self.git
```

2. **Modifiez le fichier  `.env`** dans le dossier avec:
```
TOKEN=TON_TOKEN_DISCORD
OPENAI_API_KEY=TON_API_KEY_OPENAI
PREFIX=!
```

3. **Obtenez votre token Discord:**
   - Ouvrez Discord dans votre navigateur (discord.com)
   - Appuyez sur `F12` pour ouvrir les outils de développement
   - Allez dans l'onglet **Application** (ou **Stockage**)
   - Dans le menu de gauche, développez **Local Storage** > `https://discord.com`
   - Cherchez la clé `token` et copiez sa valeur

⚠️ **NE PARTAGEZ JAMAIS VOTRE TOKEN!** Si quelqu'un a votre token, il peut contrôler votre compte.

## ▶️ Utilisation

Démarrez le selfbot:
```bash
python selfbot.py
```

## 📝 Commandes disponibles

`!ping` - Affiche la latence du bot
`!help` - Affiche ce message d'aide
`!info` - Affiche les informations du compte
`!avatar [@user]` - Affiche l'avatar d'un utilisateur
`!serverinfo` - Affiche les informations du serveur
`!userinfo [@user]` - Affiche les informations d'un utilisateur
`!say <message>` - Répète un message
`!embed <titre> | <description>` - Crée un embed
`!purge <nombre>` - Supprime vos propres messages
`!status <type>` - Change le statut (online, idle, dnd, invisible)
`!activity <type> <nom>` - Change l'activité (playing, streaming, listening, watching)
`!chameau @user <nombre>` - Expulse un utilisateur d'un canal vocal plusieurs fois
`!ai [question]` - Génère une réponse IA en utilisant le contexte du salon
`!save_backup` - Sauvegarde les salons, catégories et rôles du serveur dans un fichier JSON
`!load_backup [fichier]` - Applique un backup complet (rôles, salons, catégories) sur ce serveur

## ⚠️ Avertissements légaux

- Ce code est fourni à des fins éducatives uniquement
- L'auteur n'est pas responsable de l'utilisation de ce code
- L'utilisation de selfbots viole les ToS de Discord
- Utilisez à vos propres risques

## 🔧 Optimisations

Le bot inclut:
- Système de cooldown pour éviter les requêtes excessives
- Gestion d'erreurs optimisée
- Réduction des logs inutiles
- Forçage de l'événement ready si nécessaire

## 📄 Licence

MIT


