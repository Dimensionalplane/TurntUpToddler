# Deployment Guide

The standard deployment method is via Docker.

## Prerequisites
- Docker & Docker Compose
- `.env` file populated with `OPENAI_API_KEY`, `REPLICATE_API_TOKEN`, `ELEVENLABS_API_KEY`, and `GOOGLE_CLIENT_SECRETS_FILE`.

## Build and Run
```bash
cd hymn_remaker
docker compose build
docker compose up -d
```

## Updating (via version control)
Update your local repository, then run:
```bash
docker compose up -d --build
```
