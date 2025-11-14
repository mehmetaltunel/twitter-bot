# Twitter Bot Projesi

Bu proje, Twitter için iki farklı bot içerir:
1. **Twitter Reply Bot** - Rastgele tweet'lere AI ile cevap veren bot
2. **Twitter Trend Tweet Bot** - Trend'lerden tweet oluşturup atan bot

## 📁 Proje Yapısı

```
twitter-bot/
├── bots/                    # Bot dosyaları
│   ├── reply_bot.py        # Reply bot
│   └── trend_tweet_bot.py  # Trend tweet bot
├── logs/                    # Log dosyaları
│   ├── reply_bot.log
│   └── trend_tweet_bot.log
├── docs/                    # Dokümantasyon
│   └── API_KEYS_SETUP.md   # API key kurulum rehberi
├── .env                     # API key'leri (git'e commit etmeyin!)
├── .gitignore
├── requirements.txt         # Python paketleri
└── README.md               # Bu dosya
```

## 🤖 Botlar

### 1. Twitter Reply Bot (`bots/reply_bot.py`)

Rastgele tweet'lere absürt, komik ve dark mizahlı cevaplar veren bot.

**Özellikler:**
- Her 15 dakikada bir rastgele 1 tweet bulur
- AI ile absürt ve komik cevaplar üretir
- Hassas konuları (şehit, cenaze, deprem vb.) filtreler
- Troll tweet'lere öncelik verir
- Rate limit kontrolü yapar

**Kullanım:**
```bash
cd bots
python3 reply_bot.py
```

### 2. Twitter Trend Tweet Bot (`bots/trend_tweet_bot.py`)

Trend'lerden tweet oluşturup atan bot.

**Özellikler:**
- Her 5 dakikada bir çalışır
- `trends24.in` ve `twitter-trending.com` sitelerinden trend çeker
- En popüler 10 trend'i alır
- Rastgele 2 trend seçer
- Her trend için AI ile ağır troll tweet oluşturur
- İlk tweet hemen, ikinci tweet 1-4 dakika arası rastgele süre sonra atılır

**Kullanım:**
```bash
cd bots
python3 trend_tweet_bot.py
```

## 📋 Kurulum

### 1. Gerekli Paketleri Yükleyin

```bash
pip install -r requirements.txt
```

### 2. Playwright Tarayıcılarını Yükleyin (Opsiyonel)

```bash
playwright install chromium
```

**Not:** Playwright kurulu değilse bot yine de çalışır, ancak bazı sayfalar için alternatif yöntemler kullanır.

### 3. API Key'lerini Ayarlayın

Proje kök dizininde `.env` dosyası oluşturun:

```bash
# .env dosyasını oluştur
touch .env
```

`.env` dosyası şu şekilde olmalı:

```env
# Twitter API v2 Credentials
TWITTER_BEARER_TOKEN=your_bearer_token_here
TWITTER_API_KEY=your_api_key_here
TWITTER_API_SECRET=your_api_secret_here
TWITTER_ACCESS_TOKEN=your_access_token_here
TWITTER_ACCESS_TOKEN_SECRET=your_access_token_secret_here

# OAuth 2.0 Credentials (opsiyonel)
TWITTER_CLIENT_ID=your_client_id_here
TWITTER_CLIENT_SECRET=your_client_secret_here

# Groq API Key (AI için)
GROQ_API_KEY=your_groq_api_key_here
```

## 🔑 API Key'lerini Nasıl Alırsınız?

Detaylı bilgi için `docs/API_KEYS_SETUP.md` dosyasına bakın.

### Twitter API Key'leri

1. https://developer.twitter.com/ adresine gidin
2. Developer hesabı oluşturun (ücretsiz)
3. Yeni bir App oluşturun
4. "Keys and Tokens" sekmesinden şu bilgileri alın:
   - API Key (Consumer Key)
   - API Secret (Consumer Secret)
   - Bearer Token
   - Access Token ve Access Token Secret (oluşturmanız gerekir)

### Groq API Key

1. https://console.groq.com/ adresine gidin
2. Hesap oluşturun (ücretsiz)
3. API Keys sekmesinden yeni key oluşturun
4. Key'i kopyalayın

## ⚙️ Yapılandırma

### Reply Bot Ayarları

- **Çalışma sıklığı:** Her 15 dakikada bir
- **Tweet arama:** Rastgele 1 tweet (Twitter API minimum 10, sadece ilk 1 tanesi kullanılıyor)
- **AI Model:** `llama-3.3-70b-versatile` (Groq)

### Trend Tweet Bot Ayarları

- **Çalışma sıklığı:** Her 5 dakikada bir
- **Trend sayısı:** 10 trend çekilir, rastgele 2 tanesi seçilir
- **Tweet aralığı:** İlk tweet hemen, ikinci tweet 1-4 dakika arası rastgele
- **AI Model:** `llama-3.3-70b-versatile` (Groq)

## 📝 Log Dosyaları

Log dosyaları `logs/` klasöründe saklanır:
- `logs/reply_bot.log` - Reply bot'un tüm aktiviteleri
- `logs/trend_tweet_bot.log` - Trend tweet bot'un tüm aktiviteleri

## ⚠️ Önemli Notlar

1. **Rate Limits:** Twitter API'nin rate limit'lerine dikkat edin. Bot'lar otomatik olarak rate limit kontrolü yapar.

2. **API Key Güvenliği:** `.env` dosyasını asla git'e commit etmeyin! `.gitignore` dosyasına eklenmiştir.

3. **Yasal Sınırlar:** Bot'lar yasal sınırlar içinde kalacak şekilde tasarlanmıştır. Hassas konular otomatik olarak filtrelenir.

4. **Hassas Konu Filtreleme:** Reply bot şu konulardaki tweet'lere cevap vermez:
   - Şehit, cenaze, ölüm
   - Deprem, sel, yangın gibi afetler
   - Hastalık, kaza, trafik kazası
   - Terör, saldırı, bomba

## 🐛 Sorun Giderme

### Bot çalışmıyor

1. `.env` dosyasının doğru yapılandırıldığından emin olun
2. API key'lerin geçerli olduğunu kontrol edin
3. Gerekli paketlerin yüklü olduğunu kontrol edin: `pip install -r requirements.txt`
4. Bot'ları `bots/` klasöründen çalıştırdığınızdan emin olun

### Rate Limit Hatası

Bot otomatik olarak rate limit kontrolü yapar ve bekler. Eğer sürekli rate limit hatası alıyorsanız:
- Bot'ların çalışma sıklığını azaltın
- API key'inizin limit'lerini kontrol edin

### AI Cevap Üretmiyor

1. Groq API key'inizin geçerli olduğunu kontrol edin
2. Groq API'nin ücretsiz tier limit'lerini kontrol edin
3. Log dosyalarına bakın: `logs/reply_bot.log` veya `logs/trend_tweet_bot.log`

## 📄 Lisans

Bu proje eğitim amaçlıdır. Kendi sorumluluğunuzda kullanın.

## 🤝 Katkıda Bulunma

Pull request'ler kabul edilir. Büyük değişiklikler için önce bir issue açın.

## 📧 İletişim

Sorularınız için issue açabilirsiniz.
