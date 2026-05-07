# Supervision VPS

Dashboard de supervision système accessible via Traefik.

## Structure

```
supervision/
├── Dockerfile
├── docker-compose.yml
└── app/
    ├── server.py        ← API FastAPI + psutil
    └── static/
        └── index.html   ← Dashboard HTML/JS
```

## Déploiement

### 1. Adapter docker-compose.yml

- Remplacer `supervision.ton-domaine.com` par ton sous-domaine
- Remplacer `traefik_network` par le nom de ton réseau Traefik externe
- Remplacer le certresolver `letsencrypt` si différent

### 2. Générer le hash du mot de passe

```bash
# Installer htpasswd si besoin
apt install apache2-utils

# Générer le hash (remplacer "motdepasse")  Sµpervis0r
htpasswd -nb admin motdepasse
```

Copier la sortie dans le label `basicauth.users` du docker-compose.
⚠️ Dans le fichier YAML, chaque `$` doit être doublé en `$$`.

### 3. Lancer le conteneur

```bash
docker compose up -d --build
```

### 4. Vérifier les logs

```bash
docker compose logs -f supervision
```

## Métriques exposées

| Catégorie     | Métriques                                              |
|---------------|--------------------------------------------------------|
| CPU           | % global, par cœur, fréquence, load average 1/5/15min |
| RAM           | total, utilisé, disponible, %, swap                    |
| Disque        | par partition : total, utilisé, libre, %, fstype       |
| Réseau        | octets/paquets envoyés et reçus, erreurs               |
| Processus     | Top 8 par CPU : pid, nom, cpu%, ram%, statut           |
| Système       | uptime, boot time, nb processus, nb utilisateurs       |

## Refresh

Le dashboard se rafraîchit automatiquement toutes les **3 secondes**.
Pour modifier : changer `REFRESH_MS` dans `index.html`.
