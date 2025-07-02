# GENOKS Laboratuvar Yönetim Sistemi
## Kapsamlı Sistem Dokümantasyonu

---

## İçindekiler
1. [Sistem Genel Bakış](#sistem-genel-bakış)
2. [Mimari Yapı](#mimari-yapı)
3. [Ana Özellikler](#ana-özellikler)
4. [Kullanım Senaryoları](#kullanım-senaryoları)
5. [API Endpoint'leri](#api-endpointleri)
6. [Multi-Tenant Mimarisi](#multi-tenant-mimarisi)
7. [Güvenlik Özellikleri](#güvenlik-özellikleri)
8. [Teknik Detaylar](#teknik-detaylar)
9. [Kurulum ve Çalıştırma](#kurulum-ve-çalıştırma)
10. [Demo Senaryoları](#demo-senaryoları)

---

## Sistem Genel Bakış

**GENOKS**, modern laboratuvarlar için geliştirilmiş kapsamlı bir laboratuvar yönetim sistemidir. Sistem, çoklu kiracı (multi-tenant) mimarisi sayesinde farklı laboratuvarların tamamen izole edilmiş ortamlarda çalışmasını sağlar.

### Temel Amacı
- Laboratuvar merkezlerinin dijital dönüşümünü desteklemek
- Numune takibini kolaylaştırmak
- Kullanıcı yönetimini merkezi hale getirmek
- Veri güvenliğini maksimum seviyede sağlamak
- Ölçeklenebilir ve esnek bir altyapı sunmak

### Hedef Kullanıcılar
- **Laboratuvar Zincirleri**: Çoklu şubeli laboratuvar işletmeleri
- **Bağımsız Laboratuvarlar**: Tek merkezli laboratuvar işletmeleri
- **Hastaneler**: Kendi bünyesinde laboratuvar bulunduran sağlık kuruluşları
- **Araştırma Merkezleri**: Akademik ve özel araştırma laboratuvarları

---

## Mimari Yapı

### Teknoloji Stack'i
```
Frontend: RESTful API (Postman ile test edilebilir)
Backend: Django REST Framework
Veritabanı: PostgreSQL
Konteynerizasyon: Docker & Docker Compose
Kimlik Doğrulama: Token-based Authentication
Mimari: Multi-tenant (Çoklu Kiracı)
```

### Sistem Bileşenleri

#### 1. Ana Uygulamalar (Apps)
- **Centers**: Laboratuvar merkezi yönetimi
- **Users**: Kullanıcı ve rol yönetimi
- **Samples**: Numune takip ve yönetimi
- **Common**: Ortak fonksiyonlar ve yardımcılar

#### 2. Destekleyici Modüller
- **Middleware**: Tenant (kiracı) belirleme
- **Utils**: Tenant yardımcı fonksiyonları
- **Config**: Ortam yapılandırmaları

---

## Ana Özellikler

### 1. Merkez Yönetimi
- **Laboratuvar Oluşturma**: Yeni laboratuvar merkezleri kurma
- **Özelleştirme**: Merkez bazında ayarlar (dil, zaman dilimi, sertifikalar)
- **Soft Delete**: Güvenli silme işlemleri
- **İstatistikler**: Merkez performans metrikleri

### 2. Kullanıcı Yönetimi
- **Rol Tabanlı Erişim**: Admin, User, Viewer rolleri
- **Merkez Ataması**: Kullanıcıları belirli merkezlere atama
- **Güvenli Şifre Yönetimi**: Otomatik şifre oluşturma
- **Profil Yönetimi**: Kullanıcı bilgilerini güncelleme

### 3. Numune Takibi
- **Çoklu Numune Türleri**: Kan, İdrar, Doku, Tükürük, Diğer
- **Durum Takibi**: Beklemede, İşleniyor, Tamamlandı, Reddedildi, Arşivlendi
- **Tenant İzolasyonu**: Her merkez sadece kendi numunelerini görür
- **Detaylı Loglar**: Tüm işlemler kayıt altında

### 4. Güvenlik
- **Token Kimlik Doğrulama**: Güvenli API erişimi
- **Veri İzolasyonu**: Merkezler arası tam izolasyon
- **Rol Tabanlı Yetkilendirme**: İhtiyaç duyulan minimum yetki
- **Güvenli Şifre Politikaları**: Güçlü şifre gereksinimleri

---

## Kullanım Senaryoları

### Senaryo 1: Çoklu Şubeli Laboratuvar Zinciri
**Durum**: MediLab firması İstanbul, Ankara ve İzmir'de 3 şubesi bulunan bir laboratuvar zinciri.

**Çözüm**:
- Her şube için ayrı merkez oluşturulur
- Her merkez kendi veritabanı şemasına sahip olur
- İstanbul'daki numuneler Ankara'dan görülemez
- Her şube kendi kullanıcılarını yönetir
- Merkezi raporlama için API entegrasyonu

**Faydalar**:
- Tam veri izolasyonu
- Şube bazında özelleştirme
- Ölçeklenebilir yapı
- Güvenli veri yönetimi

### Senaryo 2: Hastane Bünyesinde Laboratuvar
**Durum**: Acıbadem Hastanesi'nin kendi laboratuvarı var ve sadece hastane personeli kullanacak.

**Çözüm**:
- Tek merkez oluşturulur
- Hastane personeli farklı rollerle sisteme dahil edilir
- Doktorlar viewer, teknisyenler user, laborant başı admin
- Hasta bazında numune takibi
- Hastane bilgi sistemi ile entegrasyon

**Faydalar**:
- Hastane ekosistemi ile uyumlu
- Departman bazında yetkilendirme
- Hasta gizliliği korunur
- Hızlı sonuç takibi

### Senaryo 3: Araştırma Laboratuvarı
**Durum**: İTÜ Moleküler Biyoloji Laboratuvarı araştırma projelerinde numune takibi yapıyor.

**Çözüm**:
- Proje bazında numune grupları
- Araştırmacılar için özel roller
- Dış laboratuvarlarla veri paylaşımı
- Araştırma protokollerine uygun süreç yönetimi

**Faydalar**:
- Akademik süreçlere uygun
- Proje bazında izolasyon
- Araştırma verilerinin güvenliği
- Bilimsel raporlama desteği

### Senaryo 4: Franchise Laboratuvar Modeli
**Durum**: BioTest markası franchise veren bir laboratuvar şirketi.

**Çözüm**:
- Her franchise için ayrı merkez
- Marka standartları merkez ayarlarında
- Franchise sahipleri admin yetkisiyle kendi merkezlerini yönetir
- Merkezi kalite kontrol ve raporlama
- Standart süreçler tüm merkezlerde aynı

**Faydalar**:
- Marka tutarlılığı
- Franchise bağımsızlığı
- Merkezi kontrol imkanı
- Hızlı yeni merkez açılışı

---

## API Endpoint'leri

### Kimlik Doğrulama
```
POST /api/auth/login/          # Giriş yapma
GET  /api/auth/user/           # Kullanıcı bilgileri
POST /api/auth/logout/         # Çıkış yapma
```

### Merkez Yönetimi
```
GET    /api/centers/           # Tüm merkezleri listele
POST   /api/centers/           # Yeni merkez oluştur
GET    /api/centers/{id}/      # Merkez detaylarını getir
PUT    /api/centers/{id}/      # Merkez bilgilerini güncelle
DELETE /api/centers/{id}/      # Merkezi sil
```

### Kullanıcı Yönetimi
```
GET    /api/users/             # Kullanıcıları listele
POST   /api/users/             # Yeni kullanıcı oluştur
GET    /api/users/{id}/        # Kullanıcı detaylarını getir
PUT    /api/users/{id}/        # Kullanıcı bilgilerini güncelle
DELETE /api/users/{id}/        # Kullanıcıyı sil
```

### Numune Yönetimi
```
GET    /api/centers/{center_id}/samples/           # Numuneleri listele
POST   /api/centers/{center_id}/samples/           # Yeni numune oluştur
GET    /api/centers/{center_id}/samples/{id}/      # Numune detaylarını getir
PUT    /api/centers/{center_id}/samples/{id}/      # Numune bilgilerini güncelle
DELETE /api/centers/{center_id}/samples/{id}/      # Numuneyi sil
```

---

## Multi-Tenant Mimarisi

### Tenant Belirleme Süreci
1. **Merkez Oluşturma**: Her merkez oluşturulduğunda unique schema_name atanır
2. **Middleware İşlemi**: Her API isteğinde hangi merkeze ait olduğu belirlenir
3. **Veritabanı Yönlendirme**: İstek ilgili merkez şemasına yönlendirilir
4. **Veri İzolasyonu**: Sadece ilgili merkez verilerine erişim sağlanır

### Teknik Detaylar
```python
# Middleware örneği
class TenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Tenant belirleme
        tenant = determine_tenant(request)
        
        # Schema switching
        connection.set_schema_to(tenant.schema_name)
        
        response = self.get_response(request)
        return response
```

### Avantajları
- **Tam İzolasyon**: Merkezler birbirlerinin verilerini göremez
- **Ölçeklenebilirlik**: Yeni merkez eklemek kolay
- **Özelleştirme**: Her merkez kendi ayarlarına sahip
- **Güvenlik**: Veri sızıntısı riski minimize

---

## Güvenlik Özellikleri

### 1. Kimlik Doğrulama
- **Token Tabanlı**: Her istek için geçerli token gerekli
- **Token Süre Sınırı**: Belirli süre sonra token'lar geçersiz olur
- **Güvenli Header**: `Authorization: Token {token}` formatı

### 2. Yetkilendirme
- **Rol Tabanlı Erişim (RBAC)**:
  - **Admin**: Tüm işlemler
  - **User**: Standart işlemler
  - **Viewer**: Sadece okuma

### 3. Veri Güvenliği
- **Tenant İzolasyonu**: Çapraz veri erişimi imkansız
- **Soft Delete**: Veriler fiziksel olarak silinmez
- **Audit Trail**: Tüm işlemler loglanır
- **Şifre Güvenliği**: Güçlü şifre politikaları

### 4. API Güvenliği
- **CORS Koruması**: Sadece izinli domainlerden erişim
- **Rate Limiting**: Aşırı istek koruması
- **Input Validation**: Tüm girdiler doğrulanır
- **SQL Injection Koruması**: ORM kullanımı

---

## Teknik Detaylar

### Veritabanı Yapısı
```sql
-- Centers tablosu
CREATE TABLE centers (
    id UUID PRIMARY KEY,
    name VARCHAR(255),
    schema_name VARCHAR(63) UNIQUE,
    settings JSONB,
    is_active BOOLEAN,
    created_at TIMESTAMP,
    deleted_at TIMESTAMP
);

-- Users tablosu
CREATE TABLE users (
    id UUID PRIMARY KEY,
    username VARCHAR(150),
    email VARCHAR(254),
    role VARCHAR(20),
    center_id UUID REFERENCES centers(id),
    is_active BOOLEAN,
    created_at TIMESTAMP
);

-- Samples tablosu (her tenant'ta)
CREATE TABLE samples (
    id UUID PRIMARY KEY,
    sample_id VARCHAR(50),
    patient_name VARCHAR(255),
    sample_type VARCHAR(20),
    status VARCHAR(20),
    collected_at TIMESTAMP,
    processed_at TIMESTAMP,
    created_at TIMESTAMP
);
```

### Konfigürasyon Yönetimi
```python
# settings.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'genoks_db',
        'USER': 'genoks_user',
        'PASSWORD': 'genoks_pass',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

# Multi-tenant setup
TENANT_MIDDLEWARE = 'middleware.tenant_middleware.TenantMiddleware'
```

---

## Kurulum ve Çalıştırma

### Gereksinimler
- Docker & Docker Compose
- Python 3.8+
- PostgreSQL 12+

### Hızlı Başlangıç
```bash
# Repository'yi klonla
git clone <repository-url>
cd genoks_case_project

# Docker ile çalıştır
docker-compose up -d

# Veritabanı migration'ları
docker-compose exec web python manage.py migrate

# Admin kullanıcı oluştur
docker-compose exec web python manage.py createsuperuser

# API test et
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "password"}'
```

### Postman Entegrasyonu
1. `Genoks_Complete_CRUD_Collection.json` dosyasını import et
2. `Genoks_API_Environment.postman_environment.json` environment'ını import et
3. Environment'ta username ve password'u güncelle
4. Collection'ı çalıştır

---

## Demo Senaryoları

### 15 Dakikalık Profesyonel Demo
1. **Giriş ve Kimlik Doğrulama** (2 dk)
   - Admin kullanıcısı ile giriş
   - Token alma süreci

2. **Merkez Yönetimi** (3 dk)
   - Yeni laboratuvar merkezi oluşturma
   - Merkez ayarlarını özelleştirme
   - Settings JSON alanı ile esneklik

3. **Kullanıcı Yönetimi** (3 dk)
   - Farklı rollerde kullanıcı oluşturma
   - Merkez ataması yapma
   - Otomatik şifre oluşturma

4. **Numune Takibi** (4 dk)
   - Çoklu numune türleri
   - Durum güncellemeleri
   - Tenant izolasyonu gösterimi

5. **Multi-Tenant Demonstrasyonu** (3 dk)
   - Farklı merkezlerden numune sorgulama
   - Veri izolasyonunu kanıtlama
   - Güvenlik özelliklerini gösterme

### Kritik Demo Noktaları
- **Veri İzolasyonu**: Merkez A'dan Merkez B'nin verilerini görememek
- **Rol Yönetimi**: Farklı rollerin farklı yetkileri
- **Ölçeklenebilirlik**: Kolayca yeni merkez eklenebilmesi
- **Güvenlik**: Token tabanlı kimlik doğrulama
- **Esneklik**: JSON settings ile özelleştirme

---

## Sonuç

GENOKS Laboratuvar Yönetim Sistemi, modern laboratuvarların ihtiyaçlarını karşılamak üzere tasarlanmış kapsamlı bir çözümdür. Multi-tenant mimarisi sayesinde farklı büyüklükteki laboratuvarlar için ölçeklenebilir, güvenli ve esnek bir platform sunar.

### Ana Değer Önerileri
- **Maliyet Etkinliği**: Tek platform, çoklu müşteri
- **Güvenlik**: Bankacılık seviyesinde veri koruması
- **Esneklik**: Her müşteri kendi ihtiyaçlarına göre özelleştirme
- **Ölçeklenebilirlik**: Büyüme ile birlikte gelişen sistem
- **Entegrasyon**: Mevcut sistemlerle kolay entegrasyon

### Gelecek Roadmap
- Web arayüzü geliştirme
- Mobil uygulama
- Gelişmiş raporlama
- Machine learning entegrasyonu
- IoT cihaz entegrasyonu

---

*Bu dokümantasyon Genoks Laboratuvar Yönetim Sistemi v1.0 için hazırlanmıştır.* 