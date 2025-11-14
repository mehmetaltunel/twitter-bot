#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Twitter Trend Tweet Bot
Her 5 dakikada bir ilk 5 trend'i alır ve AI ile tweet atar.
"""

import requests
from bs4 import BeautifulSoup
import logging
from datetime import datetime
import time
import re
from typing import List, Set, Optional
from collections import Counter
import json
import os
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

# Playwright için (opsiyonel - JavaScript gerektiren sayfalar için)
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

# Logging yapılandırması
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('../logs/trend_tweet_bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class TwitterTrendTweetBot:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
        # Twitter API v2 credentials (.env dosyasından oku)
        self.api_key = os.getenv('TWITTER_API_KEY', '')
        self.api_secret = os.getenv('TWITTER_API_SECRET', '')
        self.access_token = os.getenv('TWITTER_ACCESS_TOKEN', '')
        self.access_token_secret = os.getenv('TWITTER_ACCESS_TOKEN_SECRET', '')
        
        # Groq API key (AI tweet'ler için)
        self.groq_api_key = os.getenv('GROQ_API_KEY', '')

    def get_trends24_trends(self) -> List[str]:
        """trends24.in sitesinden trendleri çeker"""
        try:
            url = "https://trends24.in/turkey/"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            trends = []
            
            # Timeline'daki trendleri bul
            timeline_sections = soup.find_all('div', class_='trend-card')
            
            # En güncel timeline bölümünü al (ilk olan)
            if timeline_sections:
                trend_items = timeline_sections[0].find_all('li')
                for item in trend_items[:20]:  # İlk 20 trend
                    text = item.get_text(strip=True)
                    if text:
                        # Sayıları ve "K" gibi karakterleri temizle
                        text = re.sub(r'\d+K?\s*$', '', text).strip()
                        if text and text not in trends:
                            trends.append(text)
            
            # Eğer timeline bulunamazsa, alternatif yöntem dene
            if not trends:
                # Table veya tag cloud'dan trendleri bul
                trend_links = soup.find_all('a', href=re.compile(r'/turkey/'))
                for link in trend_links[:30]:
                    text = link.get_text(strip=True)
                    if text and '#' in text or len(text) > 2:
                        trends.append(text)
            
            logger.info(f"trends24.in'den {len(trends)} trend bulundu")
            return trends[:20]  # İlk 20 trend
            
        except Exception as e:
            logger.error(f"trends24.in'den trend çekilirken hata: {e}")
            return []

    def get_twitter_trending_trends(self) -> List[str]:
        """twitter-trending.com sitesinden son 1 saat içindeki trendleri çeker"""
        try:
            trends = []
            url = "https://www.twitter-trending.com/turkey/tr"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Önce JSON-LD structured data'dan çek (hızlı ve güvenilir)
            json_ld_script = soup.find('script', type='application/ld+json')
            if json_ld_script:
                try:
                    structured_data = json.loads(json_ld_script.string)
                    if 'itemListElement' in structured_data:
                        # İlk 10 trend'i al (son 1 saat için yeterli)
                        for item in structured_data['itemListElement'][:10]:
                            trend_name = item.get('name', '').strip()
                            if trend_name and trend_name not in trends:
                                trends.append(trend_name)
                        if trends:
                            logger.info(f"twitter-trending.com'dan (JSON-LD - son 1 saat) {len(trends)} trend bulundu")
                            return trends[:20]
                except Exception as e:
                    logger.debug(f"JSON-LD parse hatası: {e}")
            
            # Playwright ile JavaScript'i çalıştırarak verileri çek
            if PLAYWRIGHT_AVAILABLE and not trends:
                try:
                    with sync_playwright() as p:
                        browser = p.chromium.launch(headless=True)
                        page = browser.new_page()
                        page.goto(url, wait_until='networkidle', timeout=30000)
                        
                        # JavaScript'in çalışmasını bekle
                        page.wait_for_function('window.trends && typeof window.trends === "string"', timeout=15000)
                        
                        # window.trends değişkenini al
                        trends_json = page.evaluate('window.trends')
                        browser.close()
                        
                        if trends_json:
                            data = json.loads(trends_json)
                            
                            # table1 (10 dakika önce) ve table2 (1 saat önce) içindeki trendleri al
                            for table_key in ['table1', 'table2']:
                                if table_key in data and 'trends' in data[table_key]:
                                    table_trends = data[table_key]['trends']
                                    for trend_key, trend_value in table_trends.items():
                                        trend_data = json.loads(trend_value)
                                        trend_name = trend_data[0]
                                        trend_name = unquote(trend_name).replace('+', ' ').strip()
                                        if trend_name and trend_name not in trends:
                                            trends.append(trend_name)
                            
                            if trends:
                                logger.info(f"twitter-trending.com'dan (Playwright - son 1 saat) {len(trends)} trend bulundu")
                                return trends[:20]
                except Exception as e:
                    logger.warning(f"Playwright ile yükleme başarısız: {e}")
            
            # Son çare: HTML'den tableBody'leri çek
            if not trends:
                trends = self._extract_trends_from_table_bodies(soup)
            
            logger.info(f"twitter-trending.com'dan (son 1 saat) {len(trends)} trend bulundu")
            return trends[:20]
            
        except Exception as e:
            logger.error(f"twitter-trending.com'dan trend çekilirken hata: {e}")
            return []
    
    def _extract_trends_from_table_bodies(self, soup: BeautifulSoup) -> List[str]:
        """tableBody1 ve tableBody2'den trendleri çıkarır"""
        trends = []
        table_bodies = ['tableBody1', 'tableBody2']
        
        for table_id in table_bodies:
            tbody = soup.find('tbody', id=table_id)
            if tbody:
                rows = tbody.find_all('tr', class_='tablestr')
                for row in rows:
                    link = row.find('a', title=True)
                    if link:
                        trend_name = link.get('title', '').strip()
                        if trend_name and trend_name not in trends:
                            trends.append(trend_name)
                    else:
                        data_trend = row.get('data-trendsname', '')
                        if data_trend:
                            trend_name = unquote(data_trend).replace('+', ' ').strip()
                            if trend_name and trend_name not in trends:
                                trends.append(trend_name)
                        else:
                            link = row.find('a')
                            if link:
                                trend_name = link.get_text(strip=True)
                                trend_name = re.sub(r'\d+k?\s*tweet', '', trend_name, flags=re.IGNORECASE).strip()
                                if trend_name and len(trend_name) > 1 and trend_name not in trends:
                                    trends.append(trend_name)
        
        return trends

    def get_top_10_trends(self) -> List[str]:
        """Her iki siteden trendleri çeker ve en popüler 10'unu döndürür"""
        logger.info("Trend verileri çekiliyor...")
        
        trends1 = self.get_trends24_trends()
        trends2 = self.get_twitter_trending_trends()
        
        # Her iki listedeki trendleri birleştir
        all_trends = trends1 + trends2
        
        # Trendleri say (her iki sitede de görünenler daha önemli)
        trend_counter = Counter(all_trends)
        
        # En popüler 10 trendi al
        top_trends = [trend for trend, count in trend_counter.most_common(10)]
        
        # Eğer 10'dan az varsa, sırayla ekle
        if len(top_trends) < 10:
            remaining = [t for t in all_trends if t not in top_trends]
            top_trends.extend(remaining[:10 - len(top_trends)])
        
        logger.info(f"Toplam {len(top_trends)} trend bulundu")
        return top_trends[:10]

    def generate_tweet_with_ai(self, trend: str) -> Optional[str]:
        """Groq API ile trend için ağır troll tweet yazar (ama yasal sınırlar içinde)"""
        if not self.groq_api_key:
            logger.warning("Groq API key bulunamadı!")
            return None
            
        try:
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.groq_api_key}",
                "Content-Type": "application/json"
            }
            
            prompt = f"Türkçe bir Twitter tweet'i yaz. Konu: {trend}. Tweet ağır troll, absürt, karanlık mizah içermeli ama kesinlikle yasal sınırlar içinde kalmalı. Hakaret, küfür, kişisel saldırı, nefret söylemi, şiddet içerikli veya yasadışı hiçbir şey yazma. Sadece absürt, saçma, komik, ironik ve troll bir yorum yap. Günlük konuşma dilinde, samimi ama absürt olsun. Maksimum 250 karakter. Sadece tweet metnini yaz, başka açıklama ekleme."
            
            payload = {
                "model": "llama-3.3-70b-versatile",  # Daha iyi ve güçlü model
                "messages": [
                    {"role": "system", "content": "Sen Türkçe ağır troll tweet'ler yazan bir asistansın. Absürt, karanlık mizah, ironik ve komik tweet'ler yazarsın. Ama kesinlikle yasal sınırlar içinde kalırsın - hakaret, küfür, nefret söylemi, şiddet içerikli veya yasadışı hiçbir şey yazmazsın. Sadece absürt ve komik olursun."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 1.2,  # Daha yaratıcı ve absürt olması için
                "max_tokens": 200
            }
            
            response = requests.post(url, headers=headers, json=payload, timeout=15)
            
            if response.status_code == 200:
                result = response.json()
                tweet = result['choices'][0]['message']['content'].strip()
                
                # 280 karakter limiti
                if len(tweet) > 280:
                    tweet = tweet[:277] + "..."
                
                return tweet
                
        except Exception as e:
            logger.error(f"Groq API hatası: {e}")
            
        return None

    def post_tweet(self, text: str) -> bool:
        """Twitter'a tweet at (API ile gerçek tweet atar)"""
        if not OAUTH_AVAILABLE:
            logger.error("requests_oauthlib bulunamadı! pip install requests-oauthlib")
            return False
            
        try:
            # OAuth 1.0a authentication
            auth = OAuth1(self.api_key, self.api_secret, self.access_token, self.access_token_secret)
            
            # Twitter API v2 endpoint
            url = "https://api.twitter.com/2/tweets"
            
            # Tweet içeriği
            tweet_data = {
                "text": text
            }
            
            response = requests.post(url, json=tweet_data, auth=auth, timeout=10)
            
            if response.status_code == 201:
                result = response.json()
                tweet_id = result.get('data', {}).get('id', '')
                logger.info(f"✅ Tweet başarıyla atıldı! Tweet ID: {tweet_id}")
                return True
            else:
                logger.error(f"❌ Tweet atma hatası: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Tweet atma hatası: {e}")
            return False

    def generate_tweet_with_ai(self, trend: str) -> Optional[str]:
        """Tek bir trend için ağır troll tweet yazar"""
        if not self.groq_api_key:
            logger.warning("Groq API key bulunamadı!")
            return None
        
        if not trend:
            return None
            
        try:
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.groq_api_key}",
                "Content-Type": "application/json"
            }
            
            prompt = f"Türkçe bir Twitter tweet'i yaz. Konu: {trend}. Tweet ağır troll, absürt, karanlık mizah içermeli ama kesinlikle yasal sınırlar içinde kalmalı. Hakaret, küfür, kişisel saldırı, nefret söylemi, şiddet içerikli veya yasadışı hiçbir şey yazma. Sadece absürt, saçma, komik, ironik ve troll bir yorum yap. Günlük konuşma dilinde, samimi ama absürt olsun. Maksimum 250 karakter. Sadece tweet metnini yaz, başka açıklama ekleme."
            
            payload = {
                "model": "llama-3.3-70b-versatile",  # Daha iyi ve güçlü model
                "messages": [
                    {"role": "system", "content": "Sen Türkçe ağır troll tweet'ler yazan bir asistansın. Absürt, karanlık mizah, ironik ve komik tweet'ler yazarsın. Ama kesinlikle yasal sınırlar içinde kalırsın - hakaret, küfür, nefret söylemi, şiddet içerikli veya yasadışı hiçbir şey yazmazsın. Sadece absürt ve komik olursun."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 1.2,  # Daha yaratıcı ve absürt olması için
                "max_tokens": 200
            }
            
            response = requests.post(url, headers=headers, json=payload, timeout=15)
            
            if response.status_code == 200:
                result = response.json()
                tweet = result['choices'][0]['message']['content'].strip()
                
                # 280 karakter limiti
                if len(tweet) > 280:
                    tweet = tweet[:277] + "..."
                
                return tweet
                
        except Exception as e:
            logger.error(f"Groq API hatası: {e}")
            
        return None

    def run_once(self):
        """Bir kez çalıştır: 10 trend al, rastgele 2 tanesini seç, her biri için tweet at"""
        logger.info("")
        logger.info("=" * 60)
        logger.info(f"TREND TWEET BOT - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 60)
        
        # 10 trend al
        top_10_trends = self.get_top_10_trends()
        
        if not top_10_trends or len(top_10_trends) < 2:
            logger.warning("⚠️ Yeterli trend bulunamadı! (En az 2 trend gerekli)")
            return
        
        logger.info("")
        logger.info(f"TOPLAM {len(top_10_trends)} TREND BULUNDU:")
        for i, trend in enumerate(top_10_trends, 1):
            logger.info(f"{i}. {trend}")
        logger.info("")
        
        # Rastgele 2 trend seç
        import random
        selected_trends = random.sample(top_10_trends, min(2, len(top_10_trends)))
        
        logger.info("")
        logger.info("=" * 60)
        logger.info("RASTGELE SEÇİLEN 2 TREND:")
        for i, trend in enumerate(selected_trends, 1):
            logger.info(f"{i}. {trend}")
        logger.info("=" * 60)
        logger.info("")
        
        # Her trend için ayrı tweet oluştur ve at
        for i, trend in enumerate(selected_trends, 1):
            logger.info("")
            logger.info(f"--- Trend {i}/2: {trend} ---")
            
            # AI ile tweet oluştur
            tweet_text = self.generate_tweet_with_ai(trend)
            
            if not tweet_text:
                logger.warning(f"⚠️ '{trend}' için tweet oluşturulamadı, atlanıyor...")
                continue
            
            logger.info(f"Oluşturulan tweet: {tweet_text}")
            
            # Tweet'i at
            success = self.post_tweet(tweet_text)
            
            if success:
                logger.info(f"✅ '{trend}' için tweet başarıyla atıldı!")
            else:
                logger.error(f"❌ '{trend}' için tweet atılamadı!")
            
            # İkinci tweet için rastgele bekle (1-4 dakika arası, ortalama 2.5 dakika)
            if i < len(selected_trends):
                import random
                wait_minutes = random.uniform(1.0, 4.0)  # 1-4 dakika arası rastgele
                wait_seconds = int(wait_minutes * 60)
                logger.info(f"⏳ Sonraki tweet için {wait_minutes:.1f} dakika ({wait_seconds} saniye) bekleniyor...")
                time.sleep(wait_seconds)

    def run(self):
        """Bot'u sürekli çalıştır (her 5 dakikada bir)"""
        logger.info("=" * 60)
        logger.info("Twitter Trend Tweet Bot Başlatıldı")
        logger.info("Her 5 dakikada bir TÜM trendler için ağır troll tweet atacak")
        logger.info("=" * 60)
        
        while True:
            try:
                # Bir kez çalıştır
                self.run_once()
                
                # 5 dakika bekle (300 saniye)
                wait_minutes = 5
                logger.info("")
                logger.info("=" * 60)
                logger.info(f"⏳ {wait_minutes} dakika bekleniyor... (Sonraki trend tweet'leri için)")
                logger.info("=" * 60)
                time.sleep(wait_minutes * 60)
                
            except KeyboardInterrupt:
                logger.info("")
                logger.info("Bot durduruldu (Ctrl+C)")
                break
            except Exception as e:
                logger.error(f"❌ Hata: {e}")
                logger.info("5 dakika sonra tekrar denenecek...")
                time.sleep(5 * 60)  # Hata olursa da 5 dakika bekle


def main():
    """Ana fonksiyon"""
    bot = TwitterTrendTweetBot()
    bot.run()


if __name__ == "__main__":
    main()

