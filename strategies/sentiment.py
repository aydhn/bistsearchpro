import re
import logging

logger = logging.getLogger(__name__)

class TurkishSentimentAnalyzer:
    """
    Kural tabanlı (rule-based), kelime köklerine odaklı NLP.
    Sondan eklemeli Türkçe için kök eşleştirme kullanır.
    RAM/CPU dostu, %100 yerel ve ücretsiz çözüm.
    """
    def __init__(self):
        # Pozitif kökler
        self.positive_roots = [
            'kar', 'büyü', 'art', 'temettü', 'yatırım', 'rekor',
            'anlaşma', 'ihale', 'yüksel', 'kazan', 'kâr', 'gelir',
            'güçlü', 'başarı', 'onay'
        ]

        # Negatif kökler
        self.negative_roots = [
            'zarar', 'düş', 'azal', 'ceza', 'dava', 'iptal',
            'risk', 'kriz', 'kayıp', 'uyarı', 'gerile', 'daral',
            'satış', 'soruşturma'
        ]

    def _clean_text(self, text):
        """
        Küçük harfe çevirir ve noktalama işaretlerini siler.
        Türkçe karakter dönüşümünü (I->ı vb.) basitçe ele alır.
        """
        text = text.replace("I", "ı").replace("İ", "i")
        text = text.lower()
        # Regex ile sadece harfleri ve boşlukları bırak
        text = re.sub(r'[^a-zçğıöşü\s]', '', text)
        return text.split()

    def analyze(self, text):
        """
        Metin başlığını analiz edip -1.0 ile +1.0 arasında bir skor üretir.
        """
        if not text or not isinstance(text, str):
            return 0.0

        words = self._clean_text(text)
        if not words:
            return 0.0

        score = 0.0
        match_count = 0

        for word in words:
            # Pozitif kontrol
            for p_root in self.positive_roots:
                if word.startswith(p_root):
                    score += 1.0
                    match_count += 1
                    break # Bir kelime için tek eşleşme yeterli

            # Negatif kontrol
            for n_root in self.negative_roots:
                if word.startswith(n_root):
                    score -= 1.0
                    match_count += 1
                    break

        if match_count == 0:
            return 0.0

        # Skoru normalize et (-1.0 ile +1.0 arası)
        # Çok fazla kelime eşleşse bile asimptotik olarak sınırla
        normalized_score = score / max(1, match_count)

        # En kötü durumda bile mutlak değeri 1'i geçmemesi için:
        normalized_score = max(-1.0, min(1.0, normalized_score))

        logger.debug(f"Sentiment Analysis: '{text}' -> Score: {normalized_score}")
        return normalized_score
