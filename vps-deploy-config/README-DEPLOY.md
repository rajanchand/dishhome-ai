# VPS Deploy Instructions (Without touching Zero-Trust project)

Tapai le yo project lai aafno server (`212.227.39.216`) ma host garna chahanu hunchha, ra purano project lai disturb nagarna khojnu bhayeko chha. 

Server ma purano project already port 80 ra 443 ma chalirako hola. Tyasaile, hami le yo naya project lai Nginx reverse proxy use garera **eutai server** ma run garnechau jasalai Virtual Host bhaninchha.

## Steps:

### 1. Server ma login garne
```bash
ssh root@212.227.39.216
```

### 2. DishHome project lai server ma clone garne (yadi garisaknu bhayeko chaina bhane)
```bash
git clone https://github.com/rajanchand/dishhome-ai.git
cd dishhome-ai
```

### 3. Port conflict avoid garna `.env` file milaune
Tapai ko purano project le default HTTP port 80 use gariraheko huncha. Tyasaile `.env` file ma naya project ko port change garera `3000` rakhne.

```bash
cp .env.example .env
nano .env
```
File ko tala pati yo dui line kura thapne (yadi chaina bhane):
```env
FRONTEND_PORT=3000
APP_PORT=8000
```

### 4. Docker compose run garne
```bash
docker-compose -f docker-compose.prod.yml up -d --build
```
*(Aba DishHome frontend server bhitra port 3000 ma chalcha, without touching purano project).*

### 5. Nginx set up garne
Server ma Nginx config folder ma gayera naya website ko lagi euta naya file banaune:
```bash
nano /etc/nginx/sites-available/dishhome.conf
```
Ani tyo file ma hami le diyeko `nginx.conf` ko content copy-paste garne. (Make sure to change `your-new-domain.com` to your actual domain name).

### 6. Nginx Enable ra Restart garne
```bash
ln -s /etc/nginx/sites-available/dishhome.conf /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx
```

Aba tapai ko naya domain bata DishHome AI chalchha, ra purano IP ma `zero-trust-security.org` jasta ko tastai chalchha!
