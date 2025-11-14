#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Twitter Reply Bot
Rastgele tweet'lere cevap verir, özellikle Atatürk'e hakaret edenlere özel cevaplar atar.

API KEY'LERİ NASIL ALIRSIN:
1. https://developer.twitter.com/ adresine git
2. Developer hesabı oluştur (ücretsiz)
3. Yeni bir App oluştur
4. API Key, API Secret, Bearer Token, Access Token ve Access Token Secret'ı al
5. Environment variables olarak ayarla:
   export TWITTER_BEARER_TOKEN="..."
   export TWITTER_API_KEY="..."
   export TWITTER_API_SECRET="..."
   export TWITTER_ACCESS_TOKEN="..."
   export TWITTER_ACCESS_TOKEN_SECRET="..."
   export GROQ_API_KEY="..."  # https://console.groq.com/ adresinden al
"""

import requests
import logging
from datetime import datetime
import time
import random
import os
from typing import Optional, List
import json
from urllib.parse import unquote
from dotenv import load_dotenv

# .env dosyasını yükle
load_dotenv()

# OAuth için
try:
    from requests_oauthlib import OAuth1
    OAUTH_AVAILABLE = True
except ImportError:
    OAUTH_AVAILABLE = False

# Logging yapılandırması
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('../logs/reply_bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class TwitterReplyBot:
    def __init__(self):
        # Twitter API v2 credentials (.env dosyasından oku)
        # Bearer token'ı URL decode et (%2F -> /, %3D -> =)
        bearer_token_raw = os.getenv('TWITTER_BEARER_TOKEN', '')
        self.bearer_token = unquote(bearer_token_raw) if bearer_token_raw else None
        self.api_key = os.getenv('TWITTER_API_KEY', '')
        self.api_secret = os.getenv('TWITTER_API_SECRET', '')
        # OAuth 2.0 credentials
        self.client_id = os.getenv('TWITTER_CLIENT_ID', '')
        self.client_secret = os.getenv('TWITTER_CLIENT_SECRET', '')
        # Access token ve secret
        self.access_token = os.getenv('TWITTER_ACCESS_TOKEN', '')
        self.access_token_secret = os.getenv('TWITTER_ACCESS_TOKEN_SECRET', '')
        
        # Atatürk'e hakaret içeren kelimeler (arama için)
        self.ataturk_negative_keywords = [
            "atatürk düşmanı",
            "atatürk karşıtı",
            "atatürk nefret",
            "atatürk hakaret",
            "mustafa kemal düşman",
            "kemalist düşman"
        ]
        
        # Groq API key (AI cevaplar için)
        self.groq_api_key = os.getenv('GROQ_API_KEY', '')

    def search_tweets(self, query: str, max_results: int = 10) -> Optional[List[dict]]:
        """Twitter'da tweet ara"""
        if not self.bearer_token:
            logger.warning("Twitter Bearer Token bulunamadı!")
            return None
        
        try:
            url = "https://api.twitter.com/2/tweets/search/recent"
            headers = {
                "Authorization": f"Bearer {self.bearer_token}"
            }
            params = {
                "query": query,
                "max_results": max_results,
                "tweet.fields": "created_at,author_id,public_metrics,text",
                "expansions": "author_id"
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                tweets = data.get('data', [])
                logger.info(f"{query} için {len(tweets)} tweet bulundu")
                return tweets
            else:
                logger.error(f"Twitter API hatası: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Tweet arama hatası: {e}")
            return None

    def reply_to_tweet(self, tweet_id: str, text: str, original_tweet: str = "") -> bool:
        """Tweet'e cevap ver (API ile gerçek tweet atar - Twitter API v2)"""
        try:
            logger.info("")
            logger.info("=" * 60)
            logger.info(f"TWEET ID: {tweet_id}")
            if original_tweet:
                logger.info(f"ORİJİNAL TWEET: {original_tweet}")
            logger.info(f"OLUŞTURULAN CEVAP:")
            logger.info(text)
            logger.info("=" * 60)
            
            # Twitter API v2 ile gerçek tweet at
            if OAUTH_AVAILABLE and self.api_key and self.api_secret and self.access_token and self.access_token_secret:
                try:
                    # OAuth 1.0a authentication
                    auth = OAuth1(self.api_key, self.api_secret, self.access_token, self.access_token_secret)
                    
                    # Twitter API v2 endpoint
                    url = "https://api.twitter.com/2/tweets"
                    
                    # Reply için tweet data
                    tweet_data = {
                        "text": text,
                        "reply": {
                            "in_reply_to_tweet_id": tweet_id
                        }
                    }
                    
                    response = requests.post(url, json=tweet_data, auth=auth, timeout=10)
                    
                    if response.status_code == 201:
                        result = response.json()
                        new_tweet_id = result.get('data', {}).get('id', '')
                        logger.info(f"✅ Tweet başarıyla atıldı! Yeni Tweet ID: {new_tweet_id}")
                        logger.info("")
                        return True
                    else:
                        logger.error(f"❌ Tweet atma hatası: {response.status_code} - {response.text}")
                        logger.info("")
                        return False
                    
                except requests.exceptions.RequestException as e:
                    logger.error(f"❌ İstek hatası: {e}")
                    logger.info("")
                    return False
            else:
                logger.warning("⚠️ OAuth veya API credentials eksik, sadece log'a yazıldı")
                logger.info("")
                return False
            
        except Exception as e:
            logger.error(f"❌ Hata: {e}")
            logger.info("")
            return False

    def check_ataturk_negative(self, tweet_text: str) -> bool:
        """Tweet'te Atatürk'e hakaret var mı kontrol et"""
        tweet_lower = tweet_text.lower()
        
        negative_phrases = [
            "atatürk düşman",
            "atatürk karşıt",
            "atatürk nefret",
            "atatürk hakaret",
            "mustafa kemal düşman",
            "kemalist düşman",
            "atatürk sevmiyorum",
            "atatürk nefret ediyorum"
        ]
        
        for phrase in negative_phrases:
            if phrase in tweet_lower:
                return True
        
        return False

    def should_reply_to_tweet(self, tweet_text: str) -> bool:
        """Tweet'e cevap verilmeli mi kontrol et (hassas konuları filtrele)"""
        tweet_lower = tweet_text.lower()
        
        # Cevap VERİLMEMELİ konular
        sensitive_keywords = [
            "şehit",
            "cenaze",
            "ölüm",
            "ölmüş",
            "öldü",
            "öldürüldü",
            "katledildi",
            "vuruldu",
            "kaza",
            "trafik kazası",
            "deprem",
            "sel",
            "yangın",
            "terör",
            "bomba",
            "saldırı",
            "hastane",
            "ameliyat",
            "kanser",
            "hasta",
            "rahatsız",
            "başsağlığı",
            "taziye",
            "yas",
            "acı",
            "üzüntü",
            "felaket",
            "afet",
            "yardım kampanyası",
            "bağış",
            "yardım"
        ]
        
        # Hassas konu varsa cevap verme
        for keyword in sensitive_keywords:
            if keyword in tweet_lower:
                logger.info(f"⚠️ Hassas konu tespit edildi ('{keyword}'), cevap verilmeyecek")
                return False
        
        # Troll tweet mi kontrol et (basit heuristics)
        troll_indicators = [
            "troll",
            "şaka",
            "mizah",
            "komik",
            "gül",
            "lol",
            "haha",
            "😂",
            "🤣",
            "😄"
        ]
        
        # Troll tweet ise cevap ver
        for indicator in troll_indicators:
            if indicator in tweet_lower:
                logger.info(f"✅ Troll tweet tespit edildi, cevap verilecek")
                return True
        
        # Normal tweet ise cevap ver (varsayılan)
        return True

    def generate_reply_with_ai(self, tweet_text: str, is_ataturk_negative: bool = False) -> Optional[str]:
        """AI ile absürt cevap oluştur (HER TWEET İÇİN AYRI CEVAP)"""
        if not self.groq_api_key:
            logger.error("❌ Groq API key bulunamadı! https://console.groq.com/ adresinden al ve koda ekle!")
            return None
        
        try:
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.groq_api_key}",
                "Content-Type": "application/json"
            }
            
            if is_ataturk_negative:
                # Atatürk'e hakaret edenlere özel absürt, dark mizahlı cevap
                prompt = f"""Birisi şu tweet'i attı: "{tweet_text}"

Bu kişi Atatürk'e hakaret ediyor. Ona absürt, dark mizahlı, kudurtucu ama dava edilme riski olmayan bir cevap yaz. 
- Absürt olmalı (örnek: "karpuz kestim biber çıktı" gibi)
- Dark mizah içermeli
- Onu kudurtmalı ama hakaret içermemeli
- Dava edilme riski olmamalı
- Maksimum 280 karakter
- Sadece cevabı yaz, başka açıklama ekleme"""
            else:
                # Genel absürt cevap
                prompt = f"""Birisi şu tweet'i attı: "{tweet_text}"

Buna absürt, komik, anlamsız bir cevap yaz. 
- Absürt olmalı (örnek: "karpuz kestim biber çıktı" gibi)
- Komik ve anlamsız olmalı
- Maksimum 280 karakter
- Sadece cevabı yaz, başka açıklama ekleme"""
            
            payload = {
                "model": "llama-3.3-70b-versatile",  # En güçlü model
                "messages": [
                    {"role": "system", "content": "Sen absürt, komik, dark mizahlı tweet cevapları yazan bir asistansın. Her seferinde farklı ve yaratıcı cevaplar üretirsin."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.9,  # Daha yaratıcı olması için yüksek
                "max_tokens": 200
            }
            
            response = requests.post(url, headers=headers, json=payload, timeout=15)
            
            if response.status_code == 200:
                result = response.json()
                reply = result['choices'][0]['message']['content'].strip()
                # 280 karakter limiti
                if len(reply) > 280:
                    reply = reply[:277] + "..."
                return reply
            else:
                logger.error(f"Groq API hatası: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"AI cevap üretme hatası: {e}")
            return None

    def generate_reply(self, tweet_text: str, is_ataturk_negative: bool = False) -> str:
        """Tweet için absürt cevap oluştur (AI ile - HER TWEET İÇİN AYRI)"""
        # ÖNCE AI'YI DENE
        reply = self.generate_reply_with_ai(tweet_text, is_ataturk_negative)
        
        # AI başarısız olursa fallback (ama önce AI'yı dene)
        if not reply or reply == "Karpuz kestim biber çıktı":
            logger.warning("⚠️ AI cevap üretemedi, tekrar deneniyor...")
            # Bir kez daha dene
            time.sleep(1)
            reply = self.generate_reply_with_ai(tweet_text, is_ataturk_negative)
            
            # Hala başarısızsa fallback
            if not reply:
                if is_ataturk_negative:
                    reply = "Karpuz kestim biber çıktı, sen de Atatürk'e laf atıyorsun. Mantık?"
                else:
                    reply = "Karpuz kestim biber çıktı"
                logger.warning("⚠️ AI çalışmadı, fallback cevap kullanıldı")
        
        return reply

    def search_random_tweets(self, max_results: int = 10) -> Optional[List[dict]]:
        """Rastgele popüler tweet'leri ara (trend'lerden)"""
        if not self.bearer_token:
            logger.warning("Twitter Bearer Token bulunamadı!")
            return None
        
        try:
            url = "https://api.twitter.com/2/tweets/search/recent"
            headers = {
                "Authorization": f"Bearer {self.bearer_token}"
            }
            
            params = {
                "query": "a lang:tr -is:retweet -is:reply",  # Daha temiz Türkçe tweet'ler
                "max_results": max_results,  # Twitter API minimum 10 istiyor
                "tweet.fields": "created_at,author_id,public_metrics,text",
                "expansions": "author_id"
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            # Rate limit kontrolü - 429 alırsak direkt bekle
            if response.status_code == 429:
                # Rate limit dolmuş, reset zamanını bekle
                if 'x-rate-limit-reset' in response.headers:
                    reset_time = int(response.headers['x-rate-limit-reset'])
                    current_time = int(time.time())
                    wait_seconds = reset_time - current_time + 5  # 5 saniye ekstra
                    
                    if wait_seconds > 0:
                        logger.warning(f"⏳ Rate limit doldu! {wait_seconds} saniye ({wait_seconds//60} dakika) bekleniyor...")
                        logger.warning(f"⏰ Reset zamanı: {time.ctime(reset_time)}")
                        time.sleep(wait_seconds)
                        # Tekrar dene
                        response = requests.get(url, headers=headers, params=params, timeout=10)
                else:
                    logger.error("❌ Rate limit doldu ama reset zamanı bilgisi yok!")
                    return None
            
            # Rate limit loglama
            if 'x-rate-limit-remaining' in response.headers:
                remaining = int(response.headers['x-rate-limit-remaining'])
                logger.info(f"Rate limit kalan: {remaining}")
            
            if 'x-rate-limit-reset' in response.headers:
                reset_time = int(response.headers['x-rate-limit-reset'])
                logger.info(f"Rate limit reset zamanı: {time.ctime(reset_time)}")
            
            # Başarılı istek
            if response.status_code == 200:
                data = response.json()
                tweets = data.get('data', [])
                logger.info(f"{len(tweets)} adet tweet bulundu.")
                return tweets
            
            # API hatası
            else:
                logger.error(f"Twitter API hatası: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Rastgele tweet arama hatası: {e}")
            return None

    def run_once(self):
        """Bot'u bir kez çalıştır (1 tweet bulup cevap ver)"""
        logger.info("")
        logger.info("Rastgele 1 tweet aranıyor...")
        random_tweets = self.search_random_tweets(max_results=10)  # Twitter API minimum 10 istiyor, sadece ilk 1 tanesini kullanacağız
        
        if random_tweets and len(random_tweets) > 0:
            # İlk tweet'i al
            selected_tweet = random_tweets[0]
            tweet_text = selected_tweet.get('text', '')
            tweet_id = selected_tweet.get('id', '')
            
            # Önce tweet'e cevap verilmeli mi kontrol et
            if not self.should_reply_to_tweet(tweet_text):
                logger.info(f"⚠️ Tweet atlanıyor (hassas konu): {tweet_id}")
                return False
            
            # Atatürk'e hakaret içermiyorsa normal cevap ver
            if not self.check_ataturk_negative(tweet_text):
                logger.info(f"Rastgele tweet bulundu: {tweet_id}")
                reply = self.generate_reply(tweet_text, is_ataturk_negative=False)
                self.reply_to_tweet(tweet_id, reply, original_tweet=tweet_text)
                return True
        
        return False

    def run(self):
        """Bot'u sürekli çalıştır (her 15 dakikada bir)"""
        logger.info("=" * 60)
        logger.info("Twitter Reply Bot Başlatıldı")
        logger.info("Her 15 dakikada bir tweet bulup cevap verecek")
        logger.info("=" * 60)
        
        while True:
            try:
                # Bir kez çalıştır
                success = self.run_once()
                
                if success:
                    logger.info("✅ Tweet başarıyla atıldı!")
                else:
                    logger.info("⚠️ Tweet atılamadı veya atlandı")
                
                # 15 dakika bekle (900 saniye)
                wait_minutes = 15
                logger.info("")
                logger.info(f"⏳ {wait_minutes} dakika bekleniyor... (Sonraki tweet için)")
                logger.info("=" * 60)
                time.sleep(wait_minutes * 60)
                
            except KeyboardInterrupt:
                logger.info("")
                logger.info("Bot durduruldu (Ctrl+C)")
                break
            except Exception as e:
                logger.error(f"❌ Hata: {e}")
                logger.info("15 dakika sonra tekrar denenecek...")
                time.sleep(15 * 60)  # Hata olursa da 15 dakika bekle


def main():
    """Ana fonksiyon"""
    bot = TwitterReplyBot()
    bot.run()


if __name__ == "__main__":
    main()

