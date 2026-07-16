# Переезд с Render на Oracle Cloud Always Free

Цель: бесплатный постоянный сервер (ARM, 4 vCPU / 24GB RAM), который не засыпает
и тянет тяжёлую обработку (whisper-транскрибация, ffmpeg-рендер, генерация картинок)
— в отличие от Render free-tier (512MB, засыпает).

## Шаг 1 — регистрация (руками, это твой шаг)

1. https://www.oracle.com/cloud/free/ → Start for free.
2. Понадобится email + номер телефона + банковская карта (только для верификации
   личности, с Always Free ресурсов Oracle не списывает; спишет 1$/0$ authorization hold).
3. При выборе региона (Home Region) — выбирай тот, где реально видел доступность
   Ampere A1 free-инстансов (у Oracle периодически "Out of capacity" в популярных
   регионах, например Frankfurt/Amsterdam часто забиты — если не получается,
   попробуй другой регион, это можно сделать только один раз при регистрации,
   так что если сомневаешься — спроси меня, посмотрю актуальные отчёты по доступности).
4. После регистрации подтверди email/телефон, дождись активации аккаунта (обычно сразу).

## Шаг 2 — создать инстанс

1. Cloud Console → Compute → Instances → Create Instance.
2. Image: **Ubuntu 22.04** (Canonical Ubuntu, aarch64/ARM).
3. Shape → Change shape → Ampere → **VM.Standard.A1.Flex** → выстави 4 OCPU / 24GB RAM
   (это весь бесплатный лимит, можно занять одним инстансом или разбить на несколько —
   для нас проще один).
4. Networking: оставь дефолтный VCN, "Assign a public IPv4 address" — ✅ включено.
5. Add SSH keys: вставь свой публичный ключ (`~/.ssh/id_ed25519.pub` или сгенерируй новый
   `ssh-keygen -t ed25519 -f ~/.ssh/oracle_prometey`).
6. Create.

## Шаг 3 — открыть порты (Security List)

По умолчанию Oracle блокирует всё кроме SSH (22). Нужно открыть 80/443 (и временно 8000
для теста без TLS):

Networking → Virtual Cloud Networks → (твой VCN) → Security Lists → Default Security List
→ Add Ingress Rules:
- Source CIDR `0.0.0.0/0`, IP Protocol TCP, Destination Port 80
- Source CIDR `0.0.0.0/0`, IP Protocol TCP, Destination Port 443
- (временно) Destination Port 8000 — можно убрать после того как заработает Caddy/443

Внутри самой VM Ubuntu тоже свой firewall (iptables/ufw) — открою при настройке.

## Шаг 4 — когда инстанс поднят, пришли мне

- Публичный IP инстанса
- Путь к приватному SSH-ключу (или подтверди, что использовал `~/.ssh/oracle_prometey`)

Дальше сделаю сам через SSH:
- поставлю Docker + docker compose
- залью `Dockerfile` / `docker-compose.yml` (уже готовы в репо)
- перенесу секреты (`client_secret.json`, `yt_token.json`, `config/credentials.json`)
  из локальной машины через `scp` — не через чат
- заведу `.env.prod` из `.env.prod.example` со значениями из `.secrets.env`
- подниму Caddy для авто-TLS (если заведёшь A-запись домена на IP инстанса —
  тогда сразу будет `https://`; без домена — временно по IP:8000)
- настрою `systemd`/`docker compose up -d --restart unless-stopped`, чтобы сервис
  переживал перезагрузку VM
- заменю GitHub Actions `deploy.yml` (сейчас дёргает Render Deploy Hook) на
  деплой через SSH на Oracle-инстанс

## Что уже готово в репозитории

- `Dockerfile` — python:3.12-slim + ffmpeg, аналогично требованиям проекта.
- `.dockerignore` — секреты/venv/outputs не попадают в образ.
- `docker-compose.yml` — монтирует `data/` (секреты, outputs, media) снаружи образа.
- `.env.prod.example` — список нужных переменных окружения (без значений).

## Домен (опционально, но лучше сделать)

Если хочешь `https://` без ворнинга браузера — нужен домен (даже поддомен бесплатного
DNS типа Cloudflare/afraid.org подойдёт). Направляем A-запись на публичный IP Oracle-
инстанса, Caddy сам получит сертификат Let's Encrypt. Без домена тоже можно жить —
просто `http://<IP>:8000` без шифрования (басик-авторизация будет идти открытым текстом,
что не супер).
