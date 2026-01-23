# Rapot Bot - VPS Deployment Rehberi

## Adım 1: Hetzner Cloud Console'a Giriş

1. **hetzner.com** → Sağ üst köşede "Login"
2. Giriş yaptıktan sonra **"Cloud"** yazısına tıkla
3. Veya direkt: **console.hetzner.cloud** git

---

## Adım 2: Yeni Proje Oluştur

1. Sol menüde **"+ New Project"** butonuna tıkla
2. Proje adı: `rapot-bot`
3. **"Add project"** tıkla
4. Oluşan projeye tıkla

---

## Adım 3: Sunucu Oluştur

1. **"Add Server"** butonuna tıkla (veya + işareti)

### Location (Konum):
- **Falkenstein** veya **Helsinki** seç (Türkiye'ye yakın)

### Image (İşletim Sistemi):
- **Ubuntu** seç → **22.04** seç

### Type (Sunucu Tipi):
- **Shared vCPU** sekmesinde kal
- **CX22** seç (2 vCPU, 4GB RAM - €3.79/ay)

### Networking:
- **IPv4** işaretli kalsın
- **IPv6** işaretli kalsın

### SSH Keys (Opsiyonel):
- Şimdilik atlayabilirsin, Password ile giriş yapacağız

### Name:
- `rapot-server`

2. **"Create & Buy Now"** tıkla

---

## Adım 4: Sunucu Bilgilerini Al

Sunucu oluşturulduktan sonra:

1. **IP Adresi**: `xxx.xxx.xxx.xxx` (kopyala)
2. **Root Password**: Email ile gelir veya ekranda gösterilir

---

## Adım 5: Sunucuya Bağlan

### Windows'ta:
1. **PowerShell** aç
2. Şu komutu yaz:
```
ssh root@SUNUCU_IP_ADRESI
```
3. Şifreyi gir (yazarken görünmez, normal)
4. "yes" yaz (ilk bağlantıda)

---

## Adım 6: Bu Mesajı Gör

Bağlandıktan sonra şunu görmelisin:
```
Welcome to Ubuntu 22.04 LTS
root@rapot-server:~#
```

Bu ekranı görünce bana haber ver, kurulum scriptlerini çalıştıracağız!
