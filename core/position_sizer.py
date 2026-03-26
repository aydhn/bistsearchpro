import logging

logger = logging.getLogger(__name__)

class PositionSizer:
    """
    Sermaye ve Lot Hesaplayıcı
    Bill Benter'ın metodolojisine uygun olarak, sabit tutarla işleme girmek yerine
    Kelly Kriteri (Kelly Criterion) mantığını kullanarak dinamik sermaye yönetimi yapar.
    """
    def __init__(self, max_risk_limit: float = 0.05):
        # Tek bir işlemde kasanın maksimum %5'i riske edilebilir
        self.max_risk_limit = max_risk_limit

    def calculate_kelly_fraction(self, win_rate: float, risk_reward_ratio: float) -> float:
        """
        Kısmi Kelly (Half-Kelly) Kriteri formülünü hesaplar.
        Formül: f = W - ((1 - W) / R)
        W: Kazanma Oranı (0.0 ile 1.0 arası)
        R: Risk/Ödül Oranı
        Döndürdüğü değer (f), kasanın RİSKE EDİLECEK yüzdesidir.
        """
        if risk_reward_ratio <= 0:
            logger.warning("Kelly Kriteri Hesaplaması: Risk/Ödül oranı 0 veya negatif olamaz.")
            return 0.0

        w = win_rate
        r = risk_reward_ratio

        # Tam Kelly Fraksiyonu
        kelly_fraction = w - ((1.0 - w) / r)

        # BİST manipülatif ve volatil olduğu için Half-Kelly (Kısmi Kelly) kullanıyoruz
        half_kelly = kelly_fraction / 2.0

        # Negatif sonuç çıkarsa, işlem yapılmamalıdır (Edge yoktur)
        if half_kelly <= 0:
            logger.info(f"Kelly Fraction negatif çıktı ({half_kelly:.4f}). Bu işlem istatistiksel bir avantaja sahip değil.")
            return 0.0

        # Maksimum risk limitini uygula (Örn: %5)
        final_risk_fraction = min(half_kelly, self.max_risk_limit)

        logger.debug(f"Kelly Hesabı -> W: {w:.2f}, R: {r:.2f} | Önerilen Risk: %{final_risk_fraction*100:.2f}")
        return final_risk_fraction

    def get_trade_recommendation(self, current_balance: float, entry_price: float, stop_loss: float, win_rate: float, risk_reward_ratio: float):
        """
        Portföy bakiyesi ve Kelly Kriteri verilerine göre işlem için önerilen
        lot sayısını (hisse miktarını) hesaplar.
        """
        if current_balance <= 0 or entry_price <= 0:
            return 0.0, 0.0

        risk_per_share = abs(entry_price - stop_loss)
        if risk_per_share == 0:
            return 0.0, 0.0

        # 1. Kelly ile kasanın yüzde kaçını "riske" edeceğimizi bul
        risk_fraction = self.calculate_kelly_fraction(win_rate, risk_reward_ratio)
        if risk_fraction <= 0:
            return 0.0, 0.0

        # 2. Toplam risk miktarını (TL) hesapla
        total_risk_amount = current_balance * risk_fraction

        # 3. Alınacak lot miktarını hesapla
        recommended_shares = total_risk_amount / risk_per_share

        # 4. Kasa kontrolü: Önerilen lot miktarı, kasanın toplam gücünü aşamaz
        max_affordable_shares = current_balance / entry_price
        final_shares = min(recommended_shares, max_affordable_shares)

        return risk_fraction, final_shares

    """
    [QUANT MİMARI NOTU - KELLY KRİTERİ VE BİLEŞİK GETİRİ]
    Her işleme kasanın tamamıyla (all-in) veya her seferinde sabit lotla (fixed size)
    girmek, bileşik getirinin (compound interest) yıkıcı (veya yapıcı) etkisini yanlış
    kullanmak demektir.

    Kelly Kriteri, kazanma ihtimalinin yüksek olduğu yerlerde bahis miktarını artırırken,
    riskli veya düşük olasılıklı durumlarda bahis miktarını azaltır. Bu sayede uzun vadede
    kasanın büyüme hızını (geometric growth rate) maksimize ederken, iflas ihtimalini
    (probability of ruin) sıfıra yaklaştırır.

    Ancak tam Kelly kullanmak teoride doğru olsa da, pratikte (özellikle BİST gibi
    sığ piyasalarda) devasa Drawdown'lara (sermaye erimelerine) yol açabilir. Bu nedenle
    profesyonel fon yöneticileri daima "Half-Kelly" (Yarım Kelly) veya "Fractional Kelly"
    kullanır. Bu sayede büyüme hızı çok az düşse de, volatilite ve psikolojik baskı
    dramatik şekilde azalır.
    """
