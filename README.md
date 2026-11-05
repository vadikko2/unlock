# unlock

Инфраструктура для личного VPN (AmneziaWG) и рабочего HTTP-прокси для Cursor (GOST) на VDS.

Все сервисы крутятся в Docker Compose. Единый источник правды для клиентов — файл в репозитории (`amnezia/wireguard/wg0.json`), поэтому конфигурации не потеряются при пересоздании сервера. Деплой происходит автоматически по пушу в ветку `master`.

---

## Как это устроено

Стек описан в `docker-compose.yml` и запускается на сервере в `/opt/unlock`:

1. **`amnezia-wg-easy`** — WireGuard с обфускацией Amnezia (UDP `443`) и веб-интерфейсом (TCP `51822`). Монтирует папку `./amnezia/wireguard`, где лежит `wg0.json`.
2. **`cursor-proxy`** — легковесный GOST-прокси (TCP `1080`) с базовой авторизацией для работы Cursor без разрывов стриминга.

Репозиторий **строго приватный**, так как `wg0.json` содержит приватные ключи клиентов.

---

## Настройка с нуля

1. **Сервер:** любой чистый Ubuntu VDS с установленным Docker и Compose.
2. **DNS:** A-запись домена (`24testreservation.ru`) указывает на IPv4 сервера (TTL `300`, без проксирования Cloudflare).
3. **GitHub Secrets:** в настройках репозитория прописаны секреты для деплоя:
   - `DEPLOY_HOST` — IP сервера;
   - `DEPLOY_USER` — пользователь (`root`);
   - `DEPLOY_SSH_KEY` — приватный SSH-ключ для деплоя;
   - `DEPLOY_ENV` — содержимое `.env` (шаблон в `.env.example`).
4. **Запуск:** пуш в `master` автоматически копирует файлы на сервер и поднимает контейнеры. Локально для тестов можно использовать `cp .env.example .env && docker compose up -d`.

---

## Управление клиентами VPN

Клиенты создаются локально через скрипты и коммитятся в git. Через веб-панель создавать клиентов не нужно — следующий деплой их затрёт.

```bash
# Добавить клиента и вывести его конфиг для приложения Amnezia
make add-client NAME="MacBook"

# Сохранить изменения в git (сразу улетит на сервер)
git add amnezia/wireguard/wg0.json
git commit -m "feat: add client MacBook"
git push

# Посмотреть список всех клиентов
make list-clients

# Получить конфиг уже существующего клиента
make export-client NAME="MacBook"
```

Конфиг из вывода импортируется в официальный клиент Amnezia VPN на телефоне или компьютере.

---

## Подключение Cursor через прокси

В настройках Cursor (`Cmd + Shift + P` -> `Preferences: Open User Settings (JSON)`):

```json
"http.proxy": "http://PROXY_USER:PROXY_PASSWORD@SERVER_IP:1080",
"http.proxyStrictSSL": true,
"http.proxySupport": "override",
"cursor.general.disableHttp2": true
```

- Подставляйте **прямой IP сервера**, а не домен.
- Параметр `cursor.general.disableHttp2: true` критичен: без него стриминг ответов ИИ виснет.
- После сохранения полностью перезапустите Cursor.

---

## Смена IP сервера

Если IP заблокирован или меняется сервер:

1. В панели Timeweb смените IP и обновите A-запись домена на новый адрес (TTL `300`).
2. Проверьте резолв: `dig +short 24testreservation.ru`.
3. Обновите секрет `DEPLOY_HOST` в GitHub и запустите деплой (`Actions -> Deploy to VDS -> Run workflow`).
4. В Cursor `settings.json` укажите новый IP.
5. На устройствах переподключите туннель Amnezia (домен подтянет новый IP сам, перевыпуск ключей не нужен).

*Для Cursor доступен агентский скилл `/change-ip`, автоматизирующий этот чек-лист.*

---

## Как чинить (Troubleshooting)

### VPN не подключается
1. Проверьте контейнеры на сервере:
   ```bash
   docker compose -f /opt/unlock/docker-compose.yml ps
   ```
2. Убедитесь, что WireGuard активен и видит пиров:
   ```bash
   docker exec amnezia-wg-easy wg show
   ```
3. Проверьте доступность порта UDP 443 снаружи. Если из домашней сети пинг до IP не идёт (`ping -c 3 SERVER_IP` дает 100% loss) — подсеть заблокирована провайдером, смените IP в панели хостинга.

### Cursor не работает через прокси
1. Посмотрите логи прокси в реальном времени:
   ```bash
   docker logs -f cursor-proxy
   ```
   При запросах должны появляться строки вида `[http] ... <-> api2.cursor.sh:443`.
2. Проверьте доступность с самого сервера:
   ```bash
   curl -sS -x http://USER:PASSWORD@127.0.0.1:1080 https://api.ipify.org
   ```
3. Если запросы висят — убедитесь, что в Cursor выключен HTTP/2 (`cursor.general.disableHttp2: true`) и редактор был перезапущен.

### Рассинхрон или сбой конфигурации
Так как всё хранится в git, сервер всегда можно вернуть в рабочее состояние:
```bash
cd /opt/unlock
docker compose down
docker compose up -d --build
```
`amnezia-wg-easy` заново пересоберет рабочий `wg0.conf` из подмонтированного `amnezia/wireguard/wg0.json`.
