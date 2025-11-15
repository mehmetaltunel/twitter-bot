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
        
        # Çekilen tweet'leri sakla (queue)
        self.tweet_queue = []

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
                    
                    # TWEET ATMA rate limit header'larını logla
                    if 'x-rate-limit-limit' in response.headers:
                        limit = response.headers['x-rate-limit-limit']
                        remaining = response.headers.get('x-rate-limit-remaining', 'N/A')
                        reset = response.headers.get('x-rate-limit-reset', 'N/A')
                        if reset != 'N/A':
                            reset_time = time.ctime(int(reset))
                            logger.info(f"📊 TWEET ATMA Rate Limit: {remaining}/{limit} kalan | Reset: {reset_time}")
                        else:
                            logger.info(f"📊 TWEET ATMA Rate Limit: {remaining}/{limit} kalan")
                    elif 'x-rate-limit-remaining' in response.headers:
                        remaining = response.headers['x-rate-limit-remaining']
                        logger.info(f"📊 TWEET ATMA Rate Limit: {remaining} kalan")
                    
                    # Rate limit kontrolü - 429 alırsak direkt False dön (beklemeyelim, run() tekrar deneyecek)
                    if response.status_code == 429:
                        if 'x-rate-limit-reset' in response.headers:
                            reset_time = int(response.headers['x-rate-limit-reset'])
                            current_time = int(time.time())
                            wait_seconds = reset_time - current_time
                            
                            logger.error(f"❌ Tweet ATMA rate limit doldu! Reset zamanı: {time.ctime(reset_time)} ({wait_seconds//60} dakika sonra)")
                            logger.info("💡 Tweet atma limit'i dolmuş, False dönüyor. run() fonksiyonu 1 dakika sonra tekrar deneyecek.")
                            logger.info("💡 Tweet çekme limit'i farklı, o dolmamış olabilir. Queue'da tweet varsa onlara cevap atılabilir.")
                            return False
                        else:
                            logger.error("❌ 429 hatası alındı ama x-rate-limit-reset header'ı yok!")
                            return False
                    
                    # Response kontrolü
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
            "yardım",
            # Milli günler ve bayramlar (milli takım hariç)
            "milli gün",
            "cumhuriyet bayramı",
            "zafer bayramı",
            "23 nisan",
            "19 mayıs",
            "30 ağustos",
            "29 ekim"
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

    def check_milli_takim(self, tweet_text: str) -> bool:
        """Tweet milli takım ile ilgili mi kontrol et"""
        tweet_lower = tweet_text.lower()
        milli_keywords = [
            "milli takım",
            "a milli",
            "milli futbol",
            "fifa",
            "dünya kupası",
            "play-off",
            "elemeler",
            "bizimçocuklar",
            "montella",
            "hakan çalhanoğlu",
            "galibiyet",
            "zafer",
            "tebrik",
            "tebrikler"
        ]
        
        for keyword in milli_keywords:
            if keyword in tweet_lower:
                return True
        return False

    def generate_reply_with_ai(self, tweet_text: str, is_ataturk_negative: bool = False) -> Optional[str]:
        """AI ile dark mizahlı, kudurtucu cevap oluştur (HER TWEET İÇİN AYRI CEVAP)"""
        if not self.groq_api_key:
            logger.error("❌ Groq API key bulunamadı! https://console.groq.com/ adresinden al ve koda ekle!")
            return None
        
        try:
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.groq_api_key}",
                "Content-Type": "application/json"
            }
            
            # Milli takım tweet'i mi kontrol et
            is_milli_takim = self.check_milli_takim(tweet_text)
            
            if is_ataturk_negative:
                # Atatürk'e hakaret edenlere özel absürt, dark mizahlı cevap
                prompt = f"""Birisi şu tweet'i attı: "{tweet_text}"

Bu kişi Atatürk'e hakaret ediyor. Ona dark mizahlı, kudurtucu, agresif ama dava edilme riski olmayan bir cevap yaz. 
- Dark mizah içermeli (sert, kudurtucu ama hakaret değil)
- Onu kudurtmalı, sinirlendirmeli ama küfür/hakaret içermemeli
- Alaycı, küçümseyici ton kullan ama yasal sınırlar içinde kal
- Dava edilme riski olmamalı (açık hakaret yok)
- Maksimum 280 karakter
- Sadece cevabı yaz, başka açıklama ekleme"""
            elif is_milli_takim:
                # Milli takım tweet'lerine özel troll ama dark mizah olmayan cevap
                prompt = f"""Birisi şu tweet'i attı: "{tweet_text}"

Bu tweet milli takım ile ilgili. Ona troll, eğlenceli, absürt ama dark mizah olmayan bir cevap yaz.
- Troll ve eğlenceli olmalı
- Absürt ve komik olabilir
- Dark mizah, kudurtucu veya saygısız olmamalı
- Milli takıma hakaret etme, sadece eğlenceli troll yap
- Maksimum 280 karakter
- Sadece cevabı yaz, başka açıklama ekleme"""
            else:
                # Genel dark mizahlı, kudurtucu cevap
                prompt = f"""Birisi şu tweet'i attı: "{tweet_text}"

Buna dark mizahlı, kudurtucu, agresif ama dava edilme riski olmayan bir cevap yaz. 
- Dark mizah içermeli (sert, kudurtucu ama hakaret değil)
- Alaycı, küçümseyici, kudurtucu ton kullan
- Onu sinirlendirmeli ama küfür/hakaret içermemeli
- Yasal sınırlar içinde kal (açık hakaret yok)
- Maksimum 280 karakter
- Sadece cevabı yaz, başka açıklama ekleme"""
            
            # System message'ı tweet tipine göre ayarla
            if is_milli_takim:
                system_message = "Sen troll, eğlenceli, absürt tweet cevapları yazan bir asistansın. Milli takım tweet'lerine troll ve eğlenceli cevaplar verirsin. Absürt ve komik olabilirsin ama dark mizah, kudurtucu veya saygısız olmazsın. Milli takıma hakaret etmezsin."
            else:
                system_message = "Sen dark mizahlı, kudurtucu, agresif tweet cevapları yazan bir asistansın. Alaycı, küçümseyici ama yasal sınırlar içinde kalarak kudurtucu cevaplar üretirsin. Küfür ve açık hakaret kullanmazsın ama kudurtucu olursun."
            
            payload = {
                "model": "llama-3.3-70b-versatile",  # En güçlü model
                "messages": [
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.95 if not is_milli_takim else 0.8,  # Milli takım için biraz daha düşük temperature
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
        """Tweet için dark mizahlı, kudurtucu cevap oluştur (AI ile - HER TWEET İÇİN AYRI)"""
        # ÖNCE AI'YI DENE
        reply = self.generate_reply_with_ai(tweet_text, is_ataturk_negative)
        
        # AI başarısız olursa fallback (ama önce AI'yı dene)
        if not reply:
            logger.warning("⚠️ AI cevap üretemedi, tekrar deneniyor...")
            # Bir kez daha dene
            time.sleep(1)
            reply = self.generate_reply_with_ai(tweet_text, is_ataturk_negative)
            
            # Hala başarısızsa fallback
            if not reply:
                is_milli_takim = self.check_milli_takim(tweet_text)
                if is_ataturk_negative:
                    reply = "Atatürk'e laf atıp duruyorsun, senin mantığın nerede kaldı? Bir düşün bakalım."
                elif is_milli_takim:
                    reply = "Vay be, milli takım! 🏆🇹🇷"
                else:
                    reply = "Bu ne saçmalık böyle? Bir düşün bakalım ne dediğini."
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
            
            # Rate limit kontrolü - 429 alırsak None dön (tweet çekme limit'i dolmuş, ama tweet atma limit'i farklı)
            if response.status_code == 429:
                # Tweet ÇEKME rate limit'i dolmuş (tweet ATMA limit'i farklı!)
                if 'x-rate-limit-reset' in response.headers:
                    reset_time = int(response.headers['x-rate-limit-reset'])
                    current_time = int(time.time())
                    wait_seconds = reset_time - current_time
                    
                    logger.warning(f"⏳ Tweet ÇEKME rate limit doldu! Reset: {time.ctime(reset_time)} ({wait_seconds//60} dakika sonra)")
                    logger.info("💡 Tweet çekme limit'i dolmuş ama tweet ATMA limit'i farklı. Queue'da tweet varsa onlara cevap atılabilir.")
                    # None dön, beklemeyelim (queue'da tweet varsa onlara cevap atılabilir)
                    return None
                else:
                    logger.error("❌ Rate limit doldu ama reset zamanı bilgisi yok!")
                    return None
            
            # TWEET ÇEKME rate limit header'larını logla
            if 'x-rate-limit-limit' in response.headers:
                limit = response.headers['x-rate-limit-limit']
                remaining = response.headers.get('x-rate-limit-remaining', 'N/A')
                reset = response.headers.get('x-rate-limit-reset', 'N/A')
                if reset != 'N/A':
                    reset_time = time.ctime(int(reset))
                    logger.info(f"📊 TWEET ÇEKME Rate Limit: {remaining}/{limit} kalan | Reset: {reset_time}")
                else:
                    logger.info(f"📊 TWEET ÇEKME Rate Limit: {remaining}/{limit} kalan")
            elif 'x-rate-limit-remaining' in response.headers:
                remaining = response.headers['x-rate-limit-remaining']
                logger.info(f"📊 TWEET ÇEKME Rate Limit: {remaining} kalan")
            
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
        
        # Önce queue'da tweet var mı kontrol et
        if len(self.tweet_queue) > 0:
            logger.info(f"📋 Queue'da {len(self.tweet_queue)} tweet var, önce onlara cevap atılıyor...")
            
            # Queue'dan ilk tweet'i al
            tweet_data = self.tweet_queue.pop(0)
            tweet_id = tweet_data['id']
            tweet_text = tweet_data['text']
            is_ataturk_negative = tweet_data['is_ataturk_negative']
            
            logger.info(f"🎯 Queue'dan tweet alındı: {tweet_id}")
            reply = self.generate_reply(tweet_text, is_ataturk_negative=is_ataturk_negative)
            success = self.reply_to_tweet(tweet_id, reply, original_tweet=tweet_text)
            
            if success:
                logger.info(f"✅ Queue'dan tweet başarıyla atıldı! Kalan: {len(self.tweet_queue)}")
                return True
            else:
                # Tweet atılamadı, queue'ya geri ekle (başa)
                self.tweet_queue.insert(0, tweet_data)
                logger.warning(f"⚠️ Tweet atılamadı, queue'ya geri eklendi. Queue'da {len(self.tweet_queue)} tweet var.")
                # Rate limit dolmuş, False dön (run() fonksiyonu 1 dakika sonra tekrar deneyecek)
                return False
        
        # Queue boşsa yeni tweet çek
        logger.info("Queue boş, yeni tweet çekiliyor...")
        random_tweets = self.search_random_tweets(max_results=10)  # Twitter API minimum 10 istiyor
        
        # Tweet çekme rate limit'i dolmuşsa ama queue boşsa, False dön (run() tekrar deneyecek)
        # ÖNEMLİ: Tweet çekme limit'i dolmuş olsa bile, tweet ATMA limit'i farklı!
        # Eğer queue'da tweet varsa onlara cevap atılabilir, bu yüzden beklemeyelim.
        if random_tweets is None:
            logger.warning("⚠️ Tweet ÇEKME rate limit'i dolmuş, queue boş.")
            logger.info("💡 Tweet çekme limit'i dolmuş ama tweet ATMA limit'i farklı. Queue'da tweet varsa onlara cevap atılabilir.")
            logger.info("⏳ Tweet çekme limit'i reset olana kadar bekleniyor...")
            return False
        
        if len(random_tweets) == 0:
            logger.warning("⚠️ Hiç tweet bulunamadı!")
            return False
        
        # Çekilen tweet'leri logla
        logger.info("")
        logger.info("=" * 60)
        logger.info(f"ÇEKİLEN {len(random_tweets)} TWEET:")
        logger.info("=" * 60)
        for i, tweet in enumerate(random_tweets, 1):
            tweet_text = tweet.get('text', '')
            tweet_id = tweet.get('id', '')
            # Tweet metnini kısalt (çok uzunsa)
            tweet_preview = tweet_text[:100] + "..." if len(tweet_text) > 100 else tweet_text
            logger.info(f"{i}. ID: {tweet_id} | {tweet_preview}")
        logger.info("=" * 60)
        logger.info("")
        
        # Uygun tweet'leri queue'ya ekle
        for tweet in random_tweets:
            tweet_text = tweet.get('text', '')
            tweet_id = tweet.get('id', '')
            
            # Önce tweet'e cevap verilmeli mi kontrol et
            if not self.should_reply_to_tweet(tweet_text):
                logger.info(f"⚠️ Tweet atlanıyor (hassas konu): {tweet_id[:20]}...")
                continue  # Bir sonraki tweet'i dene
            
            # Uygun tweet'i queue'ya ekle
            if not self.check_ataturk_negative(tweet_text):
                self.tweet_queue.append({
                    'id': tweet_id,
                    'text': tweet_text,
                    'is_ataturk_negative': False
                })
                logger.info(f"✅ Uygun tweet queue'ya eklendi: {tweet_id}")
        
        # Queue'dan tweet al ve cevap at
        if len(self.tweet_queue) > 0:
            logger.info("")
            logger.info(f"📋 Queue'da {len(self.tweet_queue)} tweet var, cevap atılıyor...")
            
            # Queue'dan ilk tweet'i al
            tweet_data = self.tweet_queue.pop(0)
            tweet_id = tweet_data['id']
            tweet_text = tweet_data['text']
            is_ataturk_negative = tweet_data['is_ataturk_negative']
            
            logger.info(f"🎯 Queue'dan tweet alındı: {tweet_id}")
            reply = self.generate_reply(tweet_text, is_ataturk_negative=is_ataturk_negative)
            success = self.reply_to_tweet(tweet_id, reply, original_tweet=tweet_text)
            
            if success:
                logger.info(f"✅ Queue'dan tweet başarıyla atıldı! Kalan: {len(self.tweet_queue)}")
                return True
            else:
                # Tweet atılamadı, queue'ya geri ekle (başa)
                self.tweet_queue.insert(0, tweet_data)
                logger.warning(f"⚠️ Tweet atılamadı, queue'ya geri eklendi. Queue'da {len(self.tweet_queue)} tweet var.")
                return False
        else:
            # Hiç uygun tweet bulunamadı
            logger.warning("⚠️ 10 tweet kontrol edildi, hiçbiri uygun değil (hepsi hassas konu içeriyor)")
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
                
                # Queue'da tweet varsa daha sık dene (rate limit reset olunca hemen dene)
                if len(self.tweet_queue) > 0:
                    wait_seconds = 60  # Queue'da tweet varsa 1 dakika bekle, sonra tekrar dene
                    logger.info("")
                    logger.info(f"📋 Queue'da {len(self.tweet_queue)} tweet var, {wait_seconds} saniye sonra tekrar denenecek...")
                    logger.info("=" * 60)
                    
                    # Beklerken her 15 saniyede bir log at (bot'un çalıştığını görmek için)
                    elapsed = 0
                    while elapsed < wait_seconds:
                        sleep_time = min(15, wait_seconds - elapsed)  # Her 15 saniye veya kalan süre
                        time.sleep(sleep_time)
                        elapsed += sleep_time
                        remaining = wait_seconds - elapsed
                        if remaining > 0:
                            logger.info(f"⏳ Queue'da tweet bekliyor... {remaining} saniye sonra tekrar denenecek (Queue: {len(self.tweet_queue)} tweet)")
                else:
                    # Queue boşsa 15 dakika bekle
                    wait_minutes = 15
                    logger.info("")
                    logger.info(f"⏳ Queue boş, {wait_minutes} dakika bekleniyor... (Yeni tweet çekmek için)")
                    logger.info("=" * 60)
                    time.sleep(wait_minutes * 60)
                
            except KeyboardInterrupt:
                logger.info("")
                logger.info("Bot durduruldu (Ctrl+C)")
                break
            except Exception as e:
                logger.error(f"❌ Hata: {e}")
                logger.info("60 saniye sonra tekrar denenecek...")
                time.sleep(60)  # Hata olursa 1 dakika bekle


def main():
    """Ana fonksiyon"""
    bot = TwitterReplyBot()
    bot.run()


if __name__ == "__main__":
    main()

