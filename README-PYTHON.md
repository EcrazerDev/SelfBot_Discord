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

2. **Créez un fichier `.env`** dans le dossier `Sbot` avec:
```
TOKEN=votre_token_discord_ici
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

- `!ping` - Affiche la latence du bot
- `!help` - Affiche la liste des commandes
- `!info` - Affiche les informations de votre compte
- `!avatar [@user]` - Affiche l'avatar d'un utilisateur
- `!serverinfo` - Affiche les informations du serveur actuel
- `!userinfo [@user]` - Affiche les informations d'un utilisateur
- `!say <message>` - Répète un message
- `!embed <titre> | <description>` - Crée un embed
- `!purge <nombre>` - Supprime vos propres messages (1-100)
- `!status <type>` - Change votre statut (online, idle, dnd, invisible)
- `!activity <type> <nom>` - Change votre activité (playing, streaming, listening, watching)

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

