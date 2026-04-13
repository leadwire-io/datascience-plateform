# DTNum Labs — v3 (Version Finale)

Plateforme DataLab on-premise pour le tenant Nubo (réseau interne, sans accès Internet).

## Démarrage en une commande

```bash
chmod +x start.sh
sudo ./start.sh <IP_SERVEUR>
```

Exemple pour le tenant Nubo :
```bash
sudo ./start.sh 10.10.5.20
```

Le script fait tout automatiquement en 7 étapes :
1. Vérifie Docker et docker-compose
2. Configure DNS local (/etc/hosts)
3. Nettoie les configs Nginx orphelines
4. Démarre tous les containers
5. Génère le certificat TLS auto-signé (10 ans)
6. Attend Keycloak (~60-90s)
7. Crée realm, client OIDC et utilisateurs

## URLs

| Service | URL |
|---------|-----|
| Portail DTNum Labs | https://dtnum.nubo.local |
| Status des services | https://dtnum.nubo.local/status |
| Keycloak Admin | https://dtnum.nubo.local/auth |
| MinIO Console | https://dtnum.nubo.local/minio |

## Credentials

| Service | Login | Mot de passe |
|---------|-------|-------------|
| Keycloak Admin | admin | Keycloak@2026! |
| MinIO | admin | Minio@2026! |
| admin-dtnum | admin-dtnum | Admin@2026! |
| user1 | user1 | User1@2026! |
| user2 | user2 | User2@2026! |

## Accès aux services DataLab

| Service | URL | Login |
|---------|-----|-------|
| JupyterLab | https://dtnum.nubo.local/{nom}/lab?token={token} | Token affiché dans le portail |
| RStudio | http://dtnum.nubo.local:PORT/ | rstudio / Token affiché |
| VSCode Server | http://dtnum.nubo.local:PORT/ | Token affiché |

> RStudio et VSCode utilisent un port HTTP aléatoire affiché dans le portail.

## Sur chaque poste client

Ajouter dans `/etc/hosts` :
```
<IP_SERVEUR>  dtnum.nubo.local
```

## Certificat auto-signé

Le navigateur affiche un avertissement.
Cliquer sur **Avancé** → **Continuer vers dtnum.nubo.local**.

## Arrêt

```bash
sudo docker-compose down        # arrêt sans supprimer les données
sudo docker-compose down -v     # arrêt + suppression complète
```

## En cas d'erreur KeyError: ContainerConfig (docker-compose 1.29.2)

```bash
sudo docker-compose down -v
sudo docker rm -f dtnum-cert-generator
sudo docker-compose up -d
```

## Structure des fichiers

```
dtnum-v3/
├── start.sh              ← démarrage en une commande
├── docker-compose.yml    ← stack complète
├── Dockerfile            ← image DTNum Labs
├── main.py               ← portail FastAPI
├── k8s.py                ← gestion des services Docker
├── minio_client.py       ← client MinIO
├── requirements.txt      ← dépendances Python
├── generate-cert.sh      ← génération certificat TLS
├── nginx/
│   ├── nginx.conf        ← configuration Nginx
│   └── services/         ← configs dynamiques des services
├── templates/
│   ├── index.html        ← interface portail
│   └── status.html       ← page de monitoring
└── certs/                ← certificats TLS (générés au démarrage)
```
