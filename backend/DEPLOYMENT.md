# Backend deployment notes

For Sprut MeetingBot Pipeline, the default deployment target is a local owner-controlled machine, such as a Mac mini.

Use:

```bash
cd backend
# Docker Compose v2:
docker compose up -d --build
# If your machine has the standalone binary instead:
# docker-compose up -d --build
```

The default local backend listens on:

```text
http://127.0.0.1:3001
```

Do not publish Docker images built from a working directory that contains local `.env` files, Google auth state, recordings, transcripts, screenshots, or debug videos.

The public product setup is documented in the root `README.md` and `docs/LOCAL_MAC_SETUP.md`.
