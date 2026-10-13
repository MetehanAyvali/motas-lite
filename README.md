MOTAŞ-lite: Filo Yönetimi için Uçtan Uca DevOps Projesi
Toplu taşıma filo yönetimi temalı küçük bir FastAPI servisi ve onu çevreleyen DevOps hattı: test, Docker, CI/CD, Kubernetes, yedekleme, Ansible ve Terraform.
> \*\*Not:\*\* Bu bir eğitim ve portfolyo projesidir. MOTAŞ'ın gerçek sistemleri, kodları veya verileriyle hiçbir bağlantısı yoktur; "MOTAŞ-lite" adı yalnızca toplu taşıma ve filo temasından esinlenilmiştir. Tüm veriler sentetiktir.
Bu projede neler var?
Alan	Ne yapıldı	Nerede
Uygulama	Araç, sürücü ve sefer kaydı; iki iş kuralı	`app/main.py`
Test	İş kurallarını doğrulayan otomatik testler	`tests/`
Konteyner	Multi-stage Dockerfile, root olmayan kullanıcı, healthcheck	`Dockerfile`
Yerel çalıştırma	Uygulama + PostgreSQL, sağlık kontrollü başlatma	`docker-compose.yml`
CI	Her push'ta test + imaj derleme	`.github/workflows/ci.yml`
CD	`main` dalında imajı GHCR'ye yayınlama	`.github/workflows/cd.yml`
Kubernetes	Deployment, Service, Ingress, Secret, probe'lar (k3d ile)	`k8s/`
Yedekleme	`pg\_dump` ile yedek ve geri yükleme denemesi	`scripts/backup.sh`
Sunucu kurulumu	Paketler, uygulama dağıtımı, vault ile şifre, cron	`ansible/`
Altyapı kodu	Ağ, disk, veritabanı, API (Docker sağlayıcısıyla)	`terraform/`
Mimari
```
Geliştirici --git push--> GitHub --> GitHub Actions
                                       |  1) pytest  2) docker build  3) imajı yayınla
                                       v
                                GHCR (imaj deposu)
                                       |  docker pull / k3d image import
                                       v
Tarayıcı --> Ingress --> Service --> api Pod(lar) --> db Pod (PostgreSQL + disk)
```
İş kuralları
Bakım kilometresi (10.000 km) dolan araca sefer atanamaz (HTTP 409).
Aynı sürücü veya araç, zamanı çakışan iki sefere atanamaz (HTTP 409). Art arda seferlere izin verilir (biri 09:00'da biterse diğeri 09:00'da başlayabilir).
API
Yöntem	Adres	Ne yapar
GET	`/health`	Veritabanına ulaşarak sağlık kontrolü yapar
POST	`/vehicles`	Araç ekler (aynı plaka: 409)
GET	`/vehicles`	Araçları ve bakım durumunu (`maintenance\_due`) listeler
POST	`/drivers`	Sürücü ekler
POST	`/trips`	Sefer ekler; kurallar ihlal edilirse 409/422/404
Etkileşimli dokümantasyon: `http://localhost:8000/docs`
Teknolojiler
Python 3.14 (Docker imajı), FastAPI, SQLAlchemy, PostgreSQL 18, Docker ve Docker Compose, GitHub Actions, GHCR, Kubernetes (k3d), Ansible, Terraform (Docker sağlayıcısı 4.x). Sürümler `requirements.txt` ve yapılandırma dosyalarında sabitlenmiştir.
Hızlı başlangıç
```bash
cp .env.example .env          # içindeki DB\_PASSWORD değerini değiştir
docker compose up --build
# http://localhost:8000/docs
```
Durdurmak için `docker compose down` (veriyi de silmek için `docker compose down -v`).
Test
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest -q
```
CI/CD
CI (`ci.yml`): Her push ve pull request'te bağımlılıkları kurar, testleri çalıştırır ve Docker imajını derler.
CD (`cd.yml`): `main` dalına gönderimde imajı `ghcr.io/metehanayvali/motas-lite` adresine `latest` ve `sha-...` etiketleriyle yayınlar. Kimlik doğrulama için GitHub'ın otomatik `GITHUB\_TOKEN` anahtarı kullanılır.
Sınır: Bu, otomatik dağıtımı kapsamaz; imaj yayınlanır, bir sunucuya otomatik gönderilmez.
Kubernetes (k3d)
```bash
k3d cluster create motas -p "8080:80@loadbalancer"
docker build -t motas-lite:dev .
k3d image import motas-lite:dev -c motas
kubectl create secret generic db-secret --from-literal=password='BURAYA\_SIFRE'
kubectl apply -f k8s/
kubectl get pods
# http://localhost:8080/docs
```
Denenen senaryolar: pod silindiğinde Deployment'ın yenisini açması, kopya sayısını artırma (`kubectl scale`), var olmayan imajla hatalı sürüm verip `kubectl rollout undo` ile geri alma.
Yedekleme ve geri yükleme
```bash
./scripts/backup.sh
docker compose exec db createdb -U motas fleet\_restore
docker compose exec -T db psql -U motas -d fleet\_restore < backups/DOSYA\_ADI.sql
```
Yedeğin işe yaradığı, ayrı bir veritabanına geri yüklenip kayıt sayıları karşılaştırılarak kontrol edilir.
Ansible
Ubuntu sunucuyu hazırlar: Git ve Docker kurar, kodu GitHub'dan çeker, `.env` dosyasını ansible-vault ile korunan şifreden üretir, uygulamayı compose ile yayınlar ve günlük yedek cron işini kurar. Playbook tekrar çalıştırıldığında (idempotent) gereksiz değişiklik yapmaz.
```bash
cd ansible
cp group\_vars/all/vault.yml.example group\_vars/all/vault.yml   # şifreyi düzenle
ansible-vault encrypt group\_vars/all/vault.yml
ansible-playbook playbook.yml --ask-vault-pass -K
```
Terraform
Uygulamanın altyapısını (ağ, disk, veritabanı, API) Docker sağlayıcısıyla kodla tanımlar. Uygulama 8001 portunda çalışır.
```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars   # şifreyi düzenle
terraform init
terraform plan
terraform apply
```
Denenen senaryolar: `plan` çıktısını okuma, elle silinen konteynerin (drift) `plan` tarafından yakalanması, `destroy` ile temizlik.
Güvenlik notları
Şifreler koda yazılmaz: `.env` (Git'e gönderilmez), Kubernetes Secret, ansible-vault ve `terraform.tfvars` (Git'e gönderilmez) kullanılır.
Konteyner root olmayan kullanıcıyla çalışır.
Terraform state dosyası şifreyi düz metin tutabilir; bu yüzden Git'e gönderilmez. Gerçek ekiplerde state uzak ve erişim kontrollü bir yerde saklanır.
Kubernetes Secret nesneleri varsayılan olarak şifrelenmez, yalnızca kodlanır (base64).
Tasarım kararları
Sürümleri sabitlemek: Bugün çalışan build'in yarın kırılmaması için bağımlılıklar `==` ile sabitlenmiştir. (Örnek: SQLAlchemy 2.1'de `postgresql://` adresinin varsayılan sürücüsü değiştiği için bağlantı adresinde `postgresql+psycopg2://` açıkça belirtilmiştir.)
Yapılandırmayı koddan ayırmak: Veritabanı adresi `DATABASE\_URL` ortam değişkeninden okunur; aynı kod yerelde SQLite, Docker'da PostgreSQL ile çalışır.
Multi-stage build: Derleme bağımlılıkları son imaja girmez; imaj küçük kalır.
Sınırlar ve sonraki adımlar
Bu proje bilerek sadedir. Bilinen eksikler:
Tablolar `create\_all` ile açılışta oluşturulur; gerçek projede migration aracı (ör. Alembic) kullanılmalıdır.
API'de kimlik doğrulama ve yetkilendirme yoktur.
Çakışma kontrolü uygulama katmanında yapılır; iki istek aynı anda gelirse yarış durumu (race condition) oluşabilir. Çözüm olarak veritabanı düzeyinde bir kısıt düşünülebilir.
Testler az sayıdadır (iş kuralları odaklı) ve SQLite ile çalışır.
İzleme ve alarm (Prometheus/Grafana), log toplama ve HTTPS yoktur.
Kubernetes'te veritabanı basit bir Deployment olarak çalışır; üretimde StatefulSet veya yönetilen bir veritabanı tercih edilir.
Yedekler aynı makinede tutulur; gerçek bir yedekleme stratejisinde farklı bir konuma da kopyalanmalıdır.
Terraform ve Ansible aynı uygulamayı iki farklı yolla çalıştırır; bu bilinçli bir öğrenme tercihidir, gerçek bir ekipte rolleri ayrılırdı.
