import os
import sys
import json
import sqlite3
import urllib.request
from colorama import init, Fore

init(autoreset=True)

class HealthCheck:
    """
    Ön Uçuş Kontrolü (Pre-Flight Check - Phase 24).
    Canlı sistemin sessizce çökmesini önler.
    """
    def run_all(self):
        print(Fore.CYAN + "=== ED CAPITAL SİSTEM SAĞLIK TARAMASI ===")

        # Test 1: Config
        try:
            with open("config/config.json", 'r') as f:
                json.load(f)
            print(Fore.GREEN + "[PASS] Config dosyası mevcut ve geçerli (JSON).")
        except Exception as e:
            print(Fore.RED + f"[FAIL] Config dosyası bozuk veya yok: {e}")
            sys.exit(1)

        # Test 2: Database I/O
        try:
            os.makedirs("data", exist_ok=True)
            conn = sqlite3.connect("data/health_test.db")
            conn.execute("CREATE TABLE test (id int)")
            conn.execute("INSERT INTO test VALUES (1)")
            conn.close()
            os.remove("data/health_test.db")
            print(Fore.GREEN + "[PASS] Veritabanı ve dizin Yazma/Okuma (I/O) yetkisi var.")
        except Exception as e:
            print(Fore.RED + f"[FAIL] Veritabanı (I/O) yetkisi reddedildi: {e}")
            sys.exit(1)

        # Test 3: Network (Ping yfinance / Google)
        try:
            urllib.request.urlopen("https://query1.finance.yahoo.com", timeout=5)
            print(Fore.GREEN + "[PASS] İnternet bağlantısı ve Yahoo Finance API erişimi açık.")
        except Exception as e:
            print(Fore.RED + f"[FAIL] Ağ veya API hatası (Bağlantı Yok): {e}")
            sys.exit(1)

        print(Fore.GREEN + "\nSistem Canlıya (Go-Live) Alınmaya Hazır. Fırlatma Başlıyor!")
        return True

if __name__ == "__main__":
    checker = HealthCheck()
    checker.run_all()
