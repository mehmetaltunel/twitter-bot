# Twitter API Key'leri Nasıl Alınır?

## 1. Twitter Developer Hesabı Oluştur

1. https://developer.twitter.com/ adresine git
2. "Sign up" butonuna tıkla
3. Twitter hesabınla giriş yap
4. Developer hesabı için başvuru yap (ücretsiz, birkaç dakika sürer)

## 2. App Oluştur

1. Developer portal'da "Projects & Apps" > "Create App" tıkla
2. App adı ver (örn: "My Reply Bot")
3. App oluşturulduktan sonra "Keys and Tokens" sekmesine git

## 3. API Key'leri Al

Şu bilgileri al:
- **API Key** (Consumer Key)
- **API Secret** (Consumer Secret)
- **Bearer Token** (otomatik oluşturulur)
- **Access Token** (oluşturman gerekir)
- **Access Token Secret** (oluşturman gerekir)

## 4. Environment Variables Ayarla

Terminal'de şu komutları çalıştır:

```bash
export TWITTER_BEARER_TOKEN="bearer_token_buraya"
export TWITTER_API_KEY="api_key_buraya"
export TWITTER_API_SECRET="api_secret_buraya"
export TWITTER_ACCESS_TOKEN="access_token_buraya"
export TWITTER_ACCESS_TOKEN_SECRET="access_token_secret_buraya"
export GROQ_API_KEY="groq_api_key_buraya"  # https://console.groq.com/ adresinden al
```

Veya `.env` dosyası oluştur:

```bash
TWITTER_BEARER_TOKEN=bearer_token_buraya
TWITTER_API_KEY=api_key_buraya
TWITTER_API_SECRET=api_secret_buraya
TWITTER_ACCESS_TOKEN=access_token_buraya
TWITTER_ACCESS_TOKEN_SECRET=access_token_secret_buraya
GROQ_API_KEY=groq_api_key_buraya
```

## 5. Groq API Key

1. https://console.groq.com/ adresine git
2. Hesap oluştur (ücretsiz)
3. API Keys sekmesinden yeni key oluştur
4. Key'i kopyala ve environment variable olarak ayarla

## Notlar

- Twitter API ücretsiz tier'da sınırlı istek hakkı var (ayda 10,000 tweet okuma)
- Rate limit'lere dikkat et
- API key'lerini asla public repository'lere commit etme!

