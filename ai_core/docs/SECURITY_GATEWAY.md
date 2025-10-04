
# Gateway Security (Nginx) — ACL + Basic Auth

- Включены ACL (разрешены 127.0.0.1, 10/8, 172.16/12, 192.168/16; остальным — deny).
- Включена Basic Auth (файл `services/compose/gateway/.htpasswd`).
- Сменить пароль:
  ```bash
  apk add --no-cache apache2-utils  # в контейнере nginx
  htpasswd -bc /etc/nginx/.htpasswd <user> <password>
  ```
- Прокси-пути (OpenAI совместимые):
  - `http://HOST:8080/api/scout/v1`
  - `http://HOST:8080/api/analyst/v1`
  - `http://HOST:8080/api/judge/v1`
  - `http://HOST:8080/api/judge-llamacpp/v1` (llama.cpp server)
