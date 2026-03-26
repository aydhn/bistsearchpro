import logging

logger = logging.getLogger(__name__)

class ExecutionSimulator:
    """
    Gerçekçi Kayma (Slippage) ve Komisyon Motoru.
    İcra Simülasyonu, bir sinyal geldiğinde fiyata anında, tam olarak o fiyattan
    girilmiş gibi varsaymanın yarattığı illüzyonu yok eder. Borsa İstanbul'un mikro yapı
    dinamiklerini hesaba katar.
    """

    def __init__(self, commission_rate=0.0004):
        # BİST için ortalama kurum komisyonu (Örn: on binde 4 = 0.04%)
        self.commission_rate = commission_rate

    def simulate_execution(self, entry_price: float, atr_value: float, direction: str = "LONG"):
        """
        Sinyal anındaki ATR (Volatilite) değerine bağlı olarak dinamik bir kayma modeli
        kullanarak gerçekçi gerçekleşme fiyatını (Fill Price) hesaplar.

        Piyasa çok hareketliyse (yüksek ATR), emrin gerçekleşme fiyatını %0.2 ile %0.5
        arasında aleyhimize (alımda daha pahalıya, satımda daha ucuza) kaydırır.
        """
        if entry_price <= 0 or atr_value <= 0:
            logger.warning("Simulate Execution: Geçersiz fiyat veya ATR değeri.")
            return entry_price

        try:
            # ATR'nin fiyata oranı (Volatilite Yüzdesi)
            volatility_pct = atr_value / entry_price

            # Kayma (Slippage) Oranı Hesabı
            # Düşük volatilitede az kayma (Örn: %0.1)
            # Yüksek volatilitede çok kayma (Örn: %0.5)
            # Basit formül: Volatilite Yüzdesinin %10'u kadar bir kayma varsayımı (Min %0.1, Max %0.5)
            base_slippage = volatility_pct * 0.10

            # Sınırlandırma (Min %0.1, Max %0.5)
            slippage_pct = max(0.001, min(base_slippage, 0.005))

            # Kaymayı fiyata yansıt (Aleyhimize)
            if direction.upper() == "LONG" or direction.upper() == "BUY":
                # Alırken daha pahalıya (Kayma) + Komisyon
                # Gerçek maliyet hesabı için komisyonu fiyata yedirmek
                slippage_amount = entry_price * slippage_pct
                commission_amount = entry_price * self.commission_rate

                real_entry_price = entry_price + slippage_amount + commission_amount

            else:
                # Satarken daha ucuza (Kayma) - Komisyon
                slippage_amount = entry_price * slippage_pct
                commission_amount = entry_price * self.commission_rate

                real_entry_price = entry_price - slippage_amount - commission_amount

            logger.debug(f"İcra Simülasyonu: Sinyal={entry_price:.2f}, Gerçekleşen={real_entry_price:.2f} "
                         f"(Slippage: %{slippage_pct*100:.2f}, Komisyon: %{self.commission_rate*100:.2f})")

            return real_entry_price

        except Exception as e:
            logger.error(f"Execution simulation hatası: {e}")
            return entry_price

    """
    [QUANT MİMARI NOTU - GERÇEKÇİ KAYMA (SLIPPAGE) VE KOMİSYON ETKİSİ]
    Birçok backtest yazılımı (özellikle basit TradingView stratejileri) komisyon
    ve kaymayı (slippage) göz ardı eder. %70 Win-Rate gösteren bir algoritma
    canlı piyasada batabilir. Neden?

    Yüksek frekanslı (High-Frequency) çalışan, sürekli al-sat yapan veya piyasanın
    çok hızlı hareket ettiği kırılım anlarında (Breakout) işlem yapan stratejilerin
    karşılaştığı gizli düşman 'Likidite Eksikliği'dir. Sinyal geldiğinde o fiyattan
    satıcı bulamazsın. Emir defterinin derinliğindeki üst kademelere yürümek zorunda kalırsın (Market Order).

    Ortalama bir komisyon (0.04%) ve her işlemde ufak bir kayma (%0.2), toplam
    maliyeti gidiş-dönüş %0.48 yapar! Sırf bu maliyeti çıkarmak için bile hissenin
    %0.5 yükselmesi şarttır.

    Bizim kurduğumuz düşük frekanslı, yüksek kazanma oranına odaklı bu sistem,
    işlem sayısını minimumda tutarak bu gizli maliyetin yıkıcı etkisinden
    sermayeyi korur.
    """
