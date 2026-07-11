# Bot CROUS Marseille

Ce bot surveille uniquement les logements CROUS dont l'adresse contient
`Marseille`. Il utilise directement la recherche CROUS `Marseille (13000)` de
la campagne active et envoie sur Telegram les logements qui viennent
d'apparaitre.

Le fichier `available_residences_marseille.txt` contient les offres presentes
lors du dernier controle. Une offre disparue puis remise en ligne declenche donc
une nouvelle alerte.

Le fichier `daily_summary_marseille.json` conserve les apparitions de la journee
avec leur heure de Paris. Au premier controle apres 00:00, le bot envoie un bilan
de la veille. Le bilan liste les heures d'apparition ou indique qu'aucun nouveau
logement n'a ete detecte.

## Configuration Telegram

1. Dans Telegram, ouvre `@BotFather`, lance `/newbot` et recupere le token.
2. Mets le token dans `.env` :

   ```env
   TELEGRAM_BOT_TOKEN=ton_token_botfather
   TELEGRAM_CHAT_ID=
   ```

3. Envoie `/start` a ton nouveau bot.
4. Recupere ton identifiant :

   ```powershell
   .\.venv\Scripts\python.exe get_chat_id.py
   ```

5. Ajoute la valeur affichee dans `TELEGRAM_CHAT_ID` puis teste Telegram :

   ```powershell
   .\.venv\Scripts\python.exe main.py --test-telegram --no-sound
   ```

Le fichier `.env` est ignore par Git et ne doit jamais etre publie.

## Lancement local

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py --dry-run --no-sound
.\.venv\Scripts\python.exe main.py --no-sound
```

Le mode normal utilise `CHECK_INTERVAL_SECONDS` defini dans `.env` (600
secondes actuellement). `Ctrl+C` l'arrete.
Le mode `--dry-run` verifie uniquement la recherche, sans Telegram et sans
modifier l'historique.

Le navigateur est recree a chaque controle. Si Chrome se ferme ou se
deconnecte, le bot le relance automatiquement et retente une fois sans
intervention manuelle.

## GitHub Actions

Le workflow `.github/workflows/crous-monitor.yml` effectue un controle toutes
les dix minutes. Dans `Settings > Secrets and variables > Actions`, ajoute :

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

Lance ensuite une premiere execution depuis l'onglet `Actions` avec
`Run workflow`. Le workflow conserve l'etat des disponibilites dans
`available_residences_marseille.txt` et le bilan dans
`daily_summary_marseille.json`.
