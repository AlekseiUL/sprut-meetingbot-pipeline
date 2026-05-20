# Backend development notes

This backend is bundled as the browser-recorder component of Sprut MeetingBot Pipeline.

For public setup instructions, use the repository root:

- `README.md`
- `docs/LOCAL_MAC_SETUP.md`
- `docs/ARCHITECTURE.md`
- `docs/TROUBLESHOOTING.md`

## Local backend build

```bash
cd backend
npm ci
npm run build
docker compose up -d --build
curl -sS http://127.0.0.1:3001/health
```

## Contribution boundary

When modifying backend code:

- keep upstream ScreenApp MIT attribution intact;
- do not commit `.env`, browser auth state, recordings, screenshots, or debug videos;
- keep `UPLOADER_TYPE=local` for the Sprut local-recorder quick start;
- do not log passwords, tokens, cookies, or Redis URIs containing credentials;
- run the root repository quality workflow locally before publishing.
