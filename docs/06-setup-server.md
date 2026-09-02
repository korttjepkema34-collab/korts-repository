# 06 - Server setup (home server, `server`)

Assumes Linux with Docker and Docker Compose. If the server runs something else (Windows,
unRAID, Proxmox), adapt and note it in `docs/decisions.md`.

## 1. Tailscale

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up --hostname server
tailscale ip -4      # note this IP, it is SERVER_TS_IP below
```

Apply the ACL in `scripts/tailscale-acl.example.json` from the Tailscale admin console so only the
two machines can reach the service ports.

## 2. Clone the repo

```bash
git clone <this repo> ~/studio && cd ~/studio
cp server/.env.example server/.env
# edit server/.env: set REDIS_PASSWORD, SERVER_TS_IP, GPU_MAC (for wake-on-LAN)
```

## 3. Bring up the stack

```bash
cd server
docker compose up -d
docker compose ps
```

Services: `ollama`, `redis`, `forgejo`, `orchestrator`, `syncthing`. Godot headless is a separate
image built on demand (see `server/godot-headless/`).

## 4. Pull models

```bash
docker compose exec ollama ollama pull qwen3.6:35b-a3b   # verify tag, see docs/04-models.md
docker compose exec ollama ollama pull qwen3-vl:8b
docker compose exec ollama ollama pull nomic-embed-text
```

Set `OLLAMA_NUM_THREADS=16` (already in compose) so it uses all logical cores.

## 5. Forgejo

Open `http://SERVER_TS_IP:3000`, create the admin user, create a repo named `studio`, and push this
repo to it. Add GitHub as a mirror if you want an off-site copy.

## 6. Syncthing

Open `http://SERVER_TS_IP:8384`, add the `assets/` folder, and pair with the gaming PC's Syncthing
using the device IDs. Two-way sync. Ignore pattern: nothing (the whole folder syncs).

## 7. Wake-on-LAN

```bash
sudo apt install wakeonlan
# find the gaming PC's MAC from `ipconfig /all` on Windows, put it in server/.env as GPU_MAC
scripts/wake-gpu.sh     # test it
```

Enable WoL in the gaming PC's BIOS and its network adapter's power settings.

## 8. Test the queue

```bash
cd ~/studio
python3 -m pip install -r server/orchestrator/requirements.txt
python3 scripts/enqueue_stub.py     # pushes a `stub` job
```

When the worker on the gaming PC picks it up you will see a result in
`redis-cli -a $REDIS_PASSWORD LRANGE results 0 -1`.

## 9. When the 12 GB GPU arrives

- Install the Nvidia driver and `nvidia-container-toolkit`.
- Uncomment the `deploy.resources` block for `ollama` in `docker-compose.yml`.
- Switch the orchestrator model per `docs/04-models.md` and add a second worker instance on the
  server for `image` and `music` kinds (`worker/` runs on Linux too).
