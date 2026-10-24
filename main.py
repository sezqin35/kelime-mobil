import random
import os
import re
import json
import time

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.image import Image
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.core.audio import SoundLoader
from kivy.graphics import Color, Rectangle, Line, RoundedRectangle, Quad
from kivy.animation import Animation
from kivy.metrics import dp
from kivy.utils import platform

# PC üzerinde dikey mobil telefon boyutunda başlat
if platform not in ('android', 'ios'):
    Window.size = (420, 750)

Window.softinput_mode = 'pan'

# ---------------------------------------------------------------------------
# AYARLAR
# ---------------------------------------------------------------------------
# Test ederken True kalsın (Google'ın test reklamı gösterilir, tıklamak güvenlidir).
# Google Play'e yüklemeden hemen önce False yap.
REKLAM_TEST_MODU = True

ADMOB_APP_ID = "ca-app-pub-4733411214953557~3933038318"
ADMOB_GERCEK_GECIS_ID = "ca-app-pub-4733411214953557/4410541306"
ADMOB_TEST_GECIS_ID = "ca-app-pub-3940256099942544/1033173712"

OYUN_SURESI = 120

# Soru kutusunun üstünde seviye etiketi (ÇOK KOLAY, ZOR...) gösterilsin mi?
SEVIYE_ETIKETI_GOSTER = False

# Soru zorluk planı: (seviye, kaç soru). Bu planın sonrası hep "ÇOK ZOR".
# 1 = Çok kolay, 2 = Kolay, 3 = Orta zor, 4 = Çok zor
SEVIYE_PLANI = [(1, 3), (2, 3), (3, 6)]
SEVIYE_ADLARI = {1: "ÇOK KOLAY", 2: "KOLAY", 3: "ORTA ZOR", 4: "ÇOK ZOR"}
SEVIYE_RENKLERI = {
    1: (0.2, 0.85, 0.4, 1),
    2: (0.6, 0.9, 0.2, 1),
    3: (1, 0.65, 0.1, 1),
    4: (1, 0.3, 0.3, 1),
}


def sira_seviyesi(sira):
    """Soru sırasına (0'dan başlar) göre seviyeyi döndürür."""
    toplam = 0
    for seviye, adet in SEVIYE_PLANI:
        toplam += adet
        if sira < toplam:
            return seviye
    return 4


def seviye_tahmin_et(cevap):
    """Dosyada seviye yazılmamış sorular için kaba tahmin (cevap uzunluğuna göre)."""
    n = len(re.sub(r'[\s\.\,\-]+', '', cevap))
    if n <= 5:
        return 1
    if n <= 7:
        return 2
    if n <= 9:
        return 3
    return 4

BENJAMIN_SURESI = 12
GEC_HAKKI = 3

ALTIN = (1, 0.8, 0, 1)
YESIL = (0.12, 0.7, 0.3, 1)
KIRMIZI = (0.75, 0.2, 0.2, 1)
MAVI = (0.15, 0.45, 0.75, 1)
KOYU = (0.07, 0.08, 0.12, 0.97)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# AdMob Entegrasyonu
# Yeni (Google Play) derlemede reklamlar java/.../AdHelper.java üzerinden çalışır.
# kivmob sadece eski test derlemesinde yedek olarak denenir.
KivMob = None
if platform == 'android':
    try:
        from kivmob import KivMob
    except Exception:
        KivMob = None


class YerelReklam:
    """Güncel AdMob SDK'sı ile geçiş (interstitial) reklamı.
    Java tarafı: java/com/szggames/kelimeoyunu/AdHelper.java"""

    def __init__(self, birim_id):
        from jnius import autoclass
        self._helper = autoclass('com.szggames.kelimeoyunu.AdHelper')
        self._activity = autoclass('org.kivy.android.PythonActivity').mActivity
        self._helper.init(self._activity, birim_id)

    def is_interstitial_loaded(self):
        return bool(self._helper.isLoaded())

    def request_interstitial(self):
        self._helper.load(self._activity)

    def show_interstitial(self):
        self._helper.show(self._activity)


# ---------------------------------------------------------------------------
# YARDIMCI FONKSİYONLAR
# ---------------------------------------------------------------------------
def yol(dosya_adi):
    return os.path.join(BASE_DIR, dosya_adi)


def dosya_var(dosya_adi):
    return os.path.exists(yol(dosya_adi))


def turkce_buyut(metin):
    donusum = {
        'i': 'İ', 'ı': 'I', 'ş': 'Ş', 'ğ': 'Ğ',
        'ü': 'Ü', 'ö': 'Ö', 'ç': 'Ç'
    }
    return "".join(donusum.get(k, k.upper()) for k in metin).strip()


def normalize_karsilastir(metin):
    # İ ve I harfleri karşılaştırmada eşit sayılır (VINCI / VİNCİ gibi yabancı isimler için)
    buyuk = turkce_buyut(metin).replace('İ', 'I')
    return re.sub(r'[\s\.\,\-\'\"]+', '', buyuk)


def veri_klasoru():
    """Telefonda yazılabilir klasör (skorlar burada saklanır)."""
    try:
        klasor = App.get_running_app().user_data_dir
        os.makedirs(klasor, exist_ok=True)
        return klasor
    except Exception:
        return BASE_DIR


def skorlari_oku():
    try:
        with open(os.path.join(veri_klasoru(), 'skorlar.json'), 'r', encoding='utf-8') as f:
            veri = json.load(f)
            if isinstance(veri, list):
                return veri
    except Exception:
        pass
    return []


def skor_kaydet(puan):
    """Skoru kaydeder. Yeni rekor ise True döner."""
    if puan <= 0:
        return False
    liste = skorlari_oku()
    onceki_en_yuksek = max([k.get('puan', 0) for k in liste], default=0)
    liste.append({'puan': puan, 'tarih': time.strftime('%d.%m.%Y')})
    liste.sort(key=lambda k: k.get('puan', 0), reverse=True)
    liste = liste[:10]
    try:
        with open(os.path.join(veri_klasoru(), 'skorlar.json'), 'w', encoding='utf-8') as f:
            json.dump(liste, f, ensure_ascii=False)
    except Exception:
        pass
    return puan > 0 and puan > onceki_en_yuksek


def popup_yap(baslik, icerik, boyut=(0.88, 0.5), kapanabilir=True):
    return Popup(
        title=baslik,
        content=icerik,
        size_hint=boyut,
        auto_dismiss=kapanabilir,
        background='',
        background_color=KOYU,
        overlay_color=(0, 0, 0, 0.7),
        title_color=ALTIN,
        title_size='18sp',
        title_align='center',
        separator_color=ALTIN
    )


def skor_tablosu_goster():
    kutu = BoxLayout(orientation='vertical', padding=dp(14), spacing=dp(8))
    skorlar = skorlari_oku()

    if skorlar:
        liste = BoxLayout(orientation='vertical', spacing=dp(4))
        for i, k in enumerate(skorlar[:10], start=1):
            satir = BoxLayout(size_hint_y=None, height=dp(30))
            renk = ALTIN if i == 1 else (1, 1, 1, 1)
            satir.add_widget(Label(text=f"{i}.", size_hint_x=0.15, bold=True, color=renk, font_size='16sp'))
            satir.add_widget(Label(text=str(k.get('puan', 0)), size_hint_x=0.4, bold=True, color=renk, font_size='17sp'))
            satir.add_widget(Label(text=k.get('tarih', ''), size_hint_x=0.45, color=(0.7, 0.72, 0.78, 1), font_size='14sp'))
            liste.add_widget(satir)
        kutu.add_widget(liste)
    else:
        kutu.add_widget(Label(text="Henüz skor yok.\nİlk oyununu oyna!", halign='center', font_size='17sp'))

    btn = YuvarlakButon(text="KAPAT", size_hint=(1, None), height=dp(46), renk=MAVI, bold=True, font_size='16sp')
    kutu.add_widget(btn)
    p = popup_yap('EN YÜKSEK SKORLAR', kutu, (0.88, 0.7))
    btn.bind(on_release=p.dismiss)
    p.open()


def nasil_oynanir_goster():
    kutu = BoxLayout(orientation='vertical', padding=dp(14), spacing=dp(10))
    metin = (
        f"• {OYUN_SURESI // 60} dakikan var. Sorunun cevabını bul!\n\n"
        "• HARF AL: Bir harf açar. Açılan her harf kelimenin puanını 100 düşürür.\n\n"
        f"• BENJAMİN: {BENJAMIN_SURESI} saniye içinde cevabı yazarsın. "
        "Doğruysa puan kazanırsın, yanlışsa aynı puanı kaybedersin. "
        "Hiç harf almadan bilirsen KOMBO: puan x2!\n\n"
        f"• GEÇ: {GEC_HAKKI} hakkın var. Geçilen sorular oyun sonunda gösterilir.\n\n"
        "• Benjamin sırasında ana süre durur."
    )
    lbl = Label(text=metin, halign='left', valign='top', font_size='15sp')
    lbl.bind(size=lbl.setter('text_size'))
    kutu.add_widget(lbl)
    btn = YuvarlakButon(text="ANLADIM", size_hint=(1, None), height=dp(46), renk=YESIL, bold=True, font_size='16sp')
    kutu.add_widget(btn)
    p = popup_yap('NASIL OYNANIR?', kutu, (0.92, 0.72))
    btn.bind(on_release=p.dismiss)
    p.open()


# ---------------------------------------------------------------------------
# ÖZEL BUTON SINIFLARI
# ---------------------------------------------------------------------------
class YuvarlakButon(Button):
    """Yuvarlak köşeli, gölgeli, basınca rengi değişen buton."""

    def __init__(self, renk=(0.25, 0.28, 0.35, 1), yaricap=10, kenar=None, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ''
        self.background_down = ''
        self.background_color = (0, 0, 0, 0)
        self.renk = renk
        self.yaricap = dp(yaricap)
        self.kenar = kenar
        self.bind(pos=self._ciz, size=self._ciz, state=self._ciz, disabled=self._ciz)
        self._ciz()

    def _ciz(self, *args):
        self.canvas.before.clear()
        r, g, b, a = self.renk
        if self.disabled:
            r, g, b, a = 0.25, 0.25, 0.28, 0.7
        elif self.state == 'down':
            r, g, b = r * 0.6, g * 0.6, b * 0.6
        with self.canvas.before:
            Color(0, 0, 0, 0.35)
            RoundedRectangle(pos=(self.x, self.y - dp(2)), size=self.size, radius=[self.yaricap])
            Color(r, g, b, a)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[self.yaricap])
            if self.kenar and not self.disabled:
                Color(*self.kenar)
                Line(rounded_rectangle=(self.x, self.y, self.width, self.height, self.yaricap), width=1.2)


class SadeMuzikButonu(Button):
    """Hoparlör simgeli ses aç/kapat butonu (resim dosyası gerekmez)."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.ses_acik = True
        self.background_color = (0, 0, 0, 0)
        self.background_normal = ''
        self.background_down = ''
        self.bind(pos=self._ciz, size=self._ciz, state=self._ciz)
        self._ciz()

    def durum_guncelle(self, acik):
        self.ses_acik = acik
        self._ciz()

    def _ciz(self, *args):
        self.canvas.before.clear()
        x, y, w, h = self.x, self.y, self.width, self.height
        if self.ses_acik:
            bg = (0.1, 0.55, 0.35, 0.95)
        else:
            bg = (0.3, 0.3, 0.36, 0.92)
        if self.state == 'down':
            bg = (bg[0] * 0.65, bg[1] * 0.65, bg[2] * 0.65, bg[3])

        s = h * 0.55                       # simge ölçüsü
        cx = x + w / 2 - s * 0.10          # simgeyi ortala
        cy = y + h / 2

        with self.canvas.before:
            Color(*bg)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(10)])
            Color(1, 1, 1, 0.35)
            Line(rounded_rectangle=(x, y, w, h, dp(10)), width=1)

            # Hoparlör gövdesi ve konisi
            Color(1, 1, 1, 1)
            Rectangle(pos=(cx - s * 0.55, cy - s * 0.18), size=(s * 0.28, s * 0.36))
            Quad(points=[cx - s * 0.27, cy - s * 0.18,
                         cx + s * 0.12, cy - s * 0.50,
                         cx + s * 0.12, cy + s * 0.50,
                         cx - s * 0.27, cy + s * 0.18])

            if self.ses_acik:
                # Ses dalgaları
                Line(circle=(cx + s * 0.12, cy, s * 0.32, 55, 125), width=dp(1.6))
                Line(circle=(cx + s * 0.12, cy, s * 0.58, 55, 125), width=dp(1.6))
            else:
                # Kapalı işareti (X)
                Color(1, 0.35, 0.35, 1)
                Line(points=[cx + s * 0.30, cy - s * 0.28, cx + s * 0.82, cy + s * 0.28], width=dp(2))
                Line(points=[cx + s * 0.30, cy + s * 0.28, cx + s * 0.82, cy - s * 0.28], width=dp(2))


class ResimliButon(Button):
    def __init__(self, resim_yolu, alt_yazi="", **kwargs):
        super().__init__(**kwargs)
        self.background_color = (0, 0, 0, 0)
        self.background_normal = ''
        self.background_down = ''
        self.resim_yolu = resim_yolu
        self.alt_yazi = alt_yazi

        self.img = Image(
            source=yol(self.resim_yolu),
            allow_stretch=True,
            keep_ratio=True
        )
        self.add_widget(self.img)

        self.lbl = Label(
            text=self.alt_yazi,
            font_size='13sp',
            bold=True,
            color=(1, 1, 1, 1)
        )
        self.add_widget(self.lbl)
        self.bind(pos=self._yerlesim_guncelle, size=self._yerlesim_guncelle,
                  state=self._yerlesim_guncelle, disabled=self._yerlesim_guncelle)

    def _yerlesim_guncelle(self, *args):
        self.img.size = (self.width, self.height * 0.75)
        self.img.pos = (self.x, self.y + self.height * 0.22)

        self.lbl.size = (self.width, self.height * 0.25)
        self.lbl.pos = (self.x, self.y)

        # Basılı / pasif durum geri bildirimi
        if self.disabled:
            self.img.opacity = 0.35
            self.lbl.opacity = 0.5
        elif self.state == 'down':
            self.img.opacity = 0.7
            self.lbl.opacity = 0.8
        else:
            self.img.opacity = 1
            self.lbl.opacity = 1

    def metin_guncelle(self, yeni_metin):
        self.lbl.text = yeni_metin


# ---------------------------------------------------------------------------
# GİRİŞ EKRANI
# ---------------------------------------------------------------------------
class GirisEkrani(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = FloatLayout()

        if dosya_var('Kelime_oyunu.png'):
            layout.add_widget(Image(source=yol('Kelime_oyunu.png'), allow_stretch=True, keep_ratio=False, size_hint=(1, 1)))
        else:
            with layout.canvas.before:
                Color(0.05, 0.06, 0.1, 1)
                Rectangle(pos=(0, 0), size=(5000, 5000))

        btn_basla = YuvarlakButon(
            text="BAŞLA",
            size_hint=(0.65, 0.08),
            pos_hint={'center_x': 0.5, 'y': 0.25},
            renk=(0, 0.75, 0.25, 1),
            kenar=(1, 1, 1, 0.5),
            yaricap=14,
            font_size='24sp',
            bold=True
        )
        btn_basla.bind(on_release=self.basla)
        layout.add_widget(btn_basla)

        btn_skor = YuvarlakButon(
            text="EN YÜKSEK SKORLAR",
            size_hint=(0.65, 0.065),
            pos_hint={'center_x': 0.5, 'y': 0.165},
            renk=MAVI,
            kenar=(1, 1, 1, 0.4),
            yaricap=12,
            font_size='16sp',
            bold=True
        )
        btn_skor.bind(on_release=lambda x: skor_tablosu_goster())
        layout.add_widget(btn_skor)

        btn_yardim = YuvarlakButon(
            text="NASIL OYNANIR?",
            size_hint=(0.65, 0.055),
            pos_hint={'center_x': 0.5, 'y': 0.095},
            renk=(0.25, 0.28, 0.38, 1),
            kenar=(1, 1, 1, 0.3),
            yaricap=12,
            font_size='14sp',
            bold=True
        )
        btn_yardim.bind(on_release=lambda x: nasil_oynanir_goster())
        layout.add_widget(btn_yardim)

        self.add_widget(layout)

    def basla(self, instance):
        self.manager.current = 'oyun'


# ---------------------------------------------------------------------------
# OYUN EKRANI
# ---------------------------------------------------------------------------
class OyunEkrani(Screen):
    def on_enter(self):
        self.oyunu_sifirla()

    def on_leave(self):
        if self.bg_music:
            self.bg_music.stop()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = FloatLayout()
        self.add_widget(self.layout)

        self.puan, self.sure, self.ses_durumu = 0, OYUN_SURESI, True
        self.oyun_aktif = False          # Menüdeyken süre işlemesin
        self.duraklatildi = False
        self.acilan_harfler = []
        self.benjamin_aktif = False
        self.benjamin_sure = BENJAMIN_SURESI
        self.animasyon_aktif = False
        self.gec_hakki = GEC_HAKKI
        self.benjamin_event = None
        self.girilen_tahmin = ""
        self.yanlis_cevaplananlar = []
        self.geri_sayim_caldi = False
        self.mevcut_soru = None
        self.mevcut_soru_degeri = 0
        self.soru_sirasi = 0
        self.cikis_popup = None

        self.ses_havuzu = {}
        self._sesleri_yukle()

        if dosya_var('studyo.png'):
            self.layout.add_widget(Image(source=yol('studyo.png'), allow_stretch=True, keep_ratio=False, size_hint=(1, 1)))

        self.ust_panel_bg = Label(size_hint=(1, 0.08), pos_hint={'top': 1})
        with self.ust_panel_bg.canvas.before:
            Color(0.05, 0.05, 0.08, 0.95)
            self.rect_bg = Rectangle(size=self.ust_panel_bg.size, pos=self.ust_panel_bg.pos)
        self.ust_panel_bg.bind(pos=self._update_panel_rect, size=self._update_panel_rect)
        self.layout.add_widget(self.ust_panel_bg)

        self.btn_ses = SadeMuzikButonu(
            size_hint=(None, None),
            size=(dp(46), dp(38)),
            pos_hint={'right': 0.98, 'top': 0.99}
        )
        self.btn_ses.bind(on_release=self.ses_degistir)
        self.layout.add_widget(self.btn_ses)

        self.bilgi_label = Label(
            text="",
            markup=True,
            font_size='17sp',
            bold=True,
            color=(1, 1, 1, 1),
            pos_hint={'x': 0.02, 'top': 0.99},
            size_hint=(0.62, 0.06),
            halign='left',
            valign='middle'
        )
        self.bilgi_label.bind(size=self.bilgi_label.setter('text_size'))
        self.layout.add_widget(self.bilgi_label)

        self.soru_container = BoxLayout(size_hint=(0.92, 0.13), pos_hint={'center_x': 0.5, 'center_y': 0.72},
                                        padding=[dp(8), dp(4)])
        with self.soru_container.canvas.before:
            Color(0, 0, 0, 0.82)
            self.soru_bg = RoundedRectangle(size=self.soru_container.size, pos=self.soru_container.pos, radius=[dp(12)])
            Color(0.9, 0.7, 0.1, 0.8)
            self.soru_border = Line(rounded_rectangle=(self.soru_container.x, self.soru_container.y,
                                                       self.soru_container.width, self.soru_container.height, dp(12)), width=1.2)

        self.soru_container.bind(pos=self._update_soru_bg, size=self._update_soru_bg)

        self.soru_label = Label(text="", halign='center', valign='middle', font_size='16sp', bold=True)
        self.soru_label.bind(size=self.soru_label.setter('text_size'))
        self.soru_container.add_widget(self.soru_label)
        self.layout.add_widget(self.soru_container)

        self.seviye_label = Label(
            text="", bold=True, font_size='12sp',
            size_hint=(None, None), size=(dp(120), dp(22)),
            pos_hint={'center_x': 0.5, 'center_y': 0.805}
        )
        self.seviye_renk = (1, 1, 1, 1)
        with self.seviye_label.canvas.before:
            self.seviye_bg_renk = Color(0, 0, 0, 0.75)
            self.seviye_bg = RoundedRectangle(pos=self.seviye_label.pos, size=self.seviye_label.size, radius=[dp(11)])
            self.seviye_kenar_renk = Color(1, 1, 1, 1)
            self.seviye_kenar = Line(rounded_rectangle=(0, 0, 10, 10, dp(11)), width=1.2)
        self.seviye_label.bind(pos=self._update_seviye_rect, size=self._update_seviye_rect)
        if SEVIYE_ETIKETI_GOSTER:
            self.layout.add_widget(self.seviye_label)

        self.kelime_box = GridLayout(
            rows=1,
            spacing=dp(3),
            size_hint=(None, None),
            height=dp(54),
            pos_hint={'center_x': 0.5, 'center_y': 0.58}
        )
        self.layout.add_widget(self.kelime_box)

        self.alt_butonlar_kutusu = BoxLayout(
            size_hint=(0.94, 0.12),
            pos_hint={'center_x': 0.5, 'y': 0.03},
            spacing=dp(12)
        )

        self.btn_harf = ResimliButon(
            resim_yolu='harf_al.png',
            alt_yazi='HARF AL',
            size_hint=(0.33, 1)
        )
        self.btn_harf.bind(on_release=self.harf_al)
        self.alt_butonlar_kutusu.add_widget(self.btn_harf)

        self.btn_gec = ResimliButon(
            resim_yolu='soru_gec.png',
            alt_yazi=f'GEÇ ({GEC_HAKKI})',
            size_hint=(0.33, 1)
        )
        self.btn_gec.bind(on_release=self.soru_gec)
        self.alt_butonlar_kutusu.add_widget(self.btn_gec)

        self.btn_benjamin = ResimliButon(
            resim_yolu='benjamin.png',
            alt_yazi='BENJAMİN',
            size_hint=(0.33, 1)
        )
        self.btn_benjamin.bind(on_release=self.benjamin_ac)
        self.alt_butonlar_kutusu.add_widget(self.btn_benjamin)

        self.layout.add_widget(self.alt_butonlar_kutusu)

        self.tahmin_kutusu = Label(
            text="KLAVYEDEN YAZIN...",
            size_hint=(0.94, 0.06),
            pos_hint={'center_x': 0.5, 'y': 0.38},
            font_size='18sp',
            bold=True,
            color=(1, 0.85, 0.2, 1)
        )
        with self.tahmin_kutusu.canvas.before:
            Color(0.1, 0.1, 0.1, 0.95)
            self.tahmin_bg_rect = RoundedRectangle(size=self.tahmin_kutusu.size, pos=self.tahmin_kutusu.pos, radius=[dp(10)])
            Color(1, 0.8, 0, 1)
            self.tahmin_line = Line(rounded_rectangle=(self.tahmin_kutusu.x, self.tahmin_kutusu.y,
                                                       self.tahmin_kutusu.width, self.tahmin_kutusu.height, dp(10)), width=1.5)
        self.tahmin_kutusu.bind(pos=self._update_tahmin_rect, size=self._update_tahmin_rect)

        self.klavye_container = BoxLayout(
            orientation='vertical',
            size_hint=(0.98, 0.36),
            pos_hint={'center_x': 0.5, 'y': 0.01},
            spacing=dp(4)
        )
        self._sanal_klavyeyi_olustur()

        self.efekt_label = Label(
            text="",
            font_size='30sp',
            bold=True,
            opacity=0,
            pos_hint={'center_x': 0.5, 'center_y': 0.64}
        )
        self.layout.add_widget(self.efekt_label)

        self.feedback_img = Image(
            source='',
            size_hint=(0.35, 0.35),
            pos_hint={'center_x': 0.5, 'center_y': 0.58},
            opacity=0
        )
        self.layout.add_widget(self.feedback_img)

        self.soru_listesi = []
        Clock.schedule_interval(self.timer_guncelle, 1)

    # ------------------------------------------------------------------ SES
    def _sesleri_yukle(self):
        ses_dosyalari = ['dogru.mp3', 'yanlis_cevap.mp3', 'harf.mp3', 'benjamin.mp3',
                         'ses.mp3', 'geri_sayim.mp3', 'sure_bitimi.mp3']
        try:
            mevcut_dosyalar = os.listdir(BASE_DIR)
        except Exception:
            mevcut_dosyalar = []

        for s_adi in ses_dosyalari:
            hedef_dosya = None
            if os.path.exists(yol(s_adi)):
                hedef_dosya = yol(s_adi)
            else:
                for dosya in mevcut_dosyalar:
                    if dosya.lower().strip() == s_adi.lower().strip():
                        hedef_dosya = yol(dosya)
                        break

            if hedef_dosya:
                try:
                    yuklenen = SoundLoader.load(hedef_dosya)
                    if yuklenen:
                        self.ses_havuzu[s_adi] = yuklenen
                except Exception:
                    pass

        self.bg_music = self.ses_havuzu.get('ses.mp3')
        if self.bg_music:
            self.bg_music.loop = True

    def ses_cal(self, dosya_adi):
        if not self.ses_durumu:
            return

        s = self.ses_havuzu.get(dosya_adi)
        if s:
            try:
                s.stop()
                s.volume = 1.0
                s.play()
            except Exception:
                pass

    def ses_degistir(self, instance):
        self.ses_durumu = not self.ses_durumu
        self.btn_ses.durum_guncelle(self.ses_durumu)

        if self.bg_music:
            if self.ses_durumu and self.oyun_aktif:
                self.bg_music.play()
            else:
                self.bg_music.stop()

    # -------------------------------------------------------------- KLAVYE
    def _sanal_klavyeyi_olustur(self):
        rakamlar = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"]
        rakam_kutusu = BoxLayout(spacing=dp(3), size_hint_y=0.18)
        for r in rakamlar:
            b = YuvarlakButon(text=r, font_size='15sp', bold=True, renk=(0.18, 0.22, 0.28, 1), yaricap=6)
            b.bind(on_release=lambda x, val=r: self.klavye_tus_basildi(val))
            rakam_kutusu.add_widget(b)
        self.klavye_container.add_widget(rakam_kutusu)

        harf_satirlari = [
            ["Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P", "Ğ", "Ü"],
            ["A", "S", "D", "F", "G", "H", "J", "K", "L", "Ş", "İ"],
            ["Z", "X", "C", "V", "B", "N", "M", "Ö", "Ç"]
        ]

        for sira, satir in enumerate(harf_satirlari):
            satir_kutu = BoxLayout(spacing=dp(3), size_hint_y=0.20)
            for harf in satir:
                b = YuvarlakButon(text=harf, font_size='17sp', bold=True, renk=(0.25, 0.28, 0.36, 1), yaricap=6)
                b.bind(on_release=lambda x, h=harf: self.klavye_tus_basildi(h))
                satir_kutu.add_widget(b)

            # SİL tuşu: normal klavyedeki gibi son sıranın sağında, Ç'nin yanında
            if sira == len(harf_satirlari) - 1:
                btn_sil = YuvarlakButon(
                    text="SİL",
                    size_hint_x=1.7,
                    renk=KIRMIZI,
                    yaricap=6,
                    bold=True,
                    font_size='15sp'
                )
                btn_sil.bind(on_release=self.klavye_sil)
                satir_kutu.add_widget(btn_sil)

            self.klavye_container.add_widget(satir_kutu)

        alt_kutu = BoxLayout(spacing=dp(4), size_hint_y=0.22)

        btn_nokta = YuvarlakButon(text=".", size_hint=(0.18, 1), renk=(0.3, 0.35, 0.45, 1),
                                  yaricap=6, bold=True, font_size='22sp')
        btn_nokta.bind(on_release=lambda x: self.klavye_tus_basildi("."))
        alt_kutu.add_widget(btn_nokta)

        btn_bosluk = YuvarlakButon(text="BOŞLUK", size_hint=(0.50, 1), renk=(0.2, 0.4, 0.55, 1),
                                   yaricap=6, bold=True, font_size='14sp')
        btn_bosluk.bind(on_release=lambda x: self.klavye_tus_basildi(" "))
        alt_kutu.add_widget(btn_bosluk)

        btn_onay = YuvarlakButon(text="GÖNDER", size_hint=(0.32, 1), renk=YESIL,
                                 yaricap=6, bold=True, font_size='15sp')
        btn_onay.bind(on_release=lambda x: self.cevap_kontrol(None))
        alt_kutu.add_widget(btn_onay)

        self.klavye_container.add_widget(alt_kutu)

    def klavye_tus_basildi(self, karakter):
        if not self.benjamin_aktif or self.animasyon_aktif or self.duraklatildi:
            return
        if len(self.girilen_tahmin) >= 40:
            return
        self.girilen_tahmin += karakter
        self.tahmin_kutusu.text = self.girilen_tahmin

    def klavye_sil(self, instance):
        if not self.benjamin_aktif or self.animasyon_aktif or self.duraklatildi:
            return
        self.girilen_tahmin = self.girilen_tahmin[:-1]
        self.tahmin_kutusu.text = self.girilen_tahmin if self.girilen_tahmin else "KLAVYEDEN YAZIN..."

    # ------------------------------------------------------- ÇİZİM YARDIMCI
    def _update_tahmin_rect(self, inst, val):
        self.tahmin_bg_rect.pos = inst.pos
        self.tahmin_bg_rect.size = inst.size
        self.tahmin_line.rounded_rectangle = (inst.x, inst.y, inst.width, inst.height, dp(10))

    def _update_panel_rect(self, instance, value):
        self.rect_bg.pos = instance.pos
        self.rect_bg.size = instance.size

    def _update_soru_bg(self, instance, value):
        self.soru_bg.pos = instance.pos
        self.soru_bg.size = instance.size
        self.soru_border.rounded_rectangle = (instance.x, instance.y, instance.width, instance.height, dp(12))

    def _update_seviye_rect(self, inst, val):
        self.seviye_bg.pos = inst.pos
        self.seviye_bg.size = inst.size
        self.seviye_kenar.rounded_rectangle = (inst.x, inst.y, inst.width, inst.height, dp(11))

    def seviye_guncelle(self, seviye):
        renk = SEVIYE_RENKLERI.get(seviye, (1, 1, 1, 1))
        self.seviye_label.text = SEVIYE_ADLARI.get(seviye, "")
        self.seviye_label.color = renk
        self.seviye_kenar_renk.rgba = renk

    def bilgi_guncelle(self):
        skor = f"SKOR: [color=ffd400]{self.puan}[/color]"
        if self.benjamin_aktif:
            renk = 'ff4444' if self.benjamin_sure <= 3 else 'ffd400'
            sag = f"BENJAMİN: [color={renk}]{self.benjamin_sure}s[/color]"
        else:
            renk = 'ff4444' if self.sure <= 10 else 'ffffff'
            sag = f"SÜRE: [color={renk}]{self.sure // 60:02d}:{self.sure % 60:02d}[/color]"
        self.bilgi_label.text = f"{skor}   |   {sag}"

    def kelime_guncelle(self):
        self.kelime_box.clear_widgets()
        if not self.mevcut_soru:
            return

        cevap = self.mevcut_soru["cevap"]
        if len(cevap) == 0:
            return

        noktalama = (".", ",", "-")
        n_harf = len([h for h in cevap if h not in (" ",) + noktalama])
        n_bosluk = cevap.count(" ")
        n_nokta = len([h for h in cevap if h in noktalama])
        if n_harf == 0:
            return

        aralik = self.kelime_box.spacing[0] if isinstance(self.kelime_box.spacing, (list, tuple)) else self.kelime_box.spacing
        bosluk_w = dp(10)
        nokta_w = dp(12)

        kullanilabilir = Window.width * 0.94 - aralik * (len(cevap) - 1) - n_bosluk * bosluk_w - n_nokta * nokta_w
        kutu_genisligi = max(dp(14), min(kullanilabilir / n_harf, dp(44)))
        self.kelime_box.width = (kutu_genisligi * n_harf + n_bosluk * bosluk_w + n_nokta * nokta_w
                                 + aralik * (len(cevap) - 1))
        f_size = max(dp(12), kutu_genisligi * 0.62)

        cevap_temiz = re.sub(r'[\s\.\,\-]+', '', cevap)
        self.mevcut_soru_degeri = (len(cevap_temiz) * 100) - (len(self.acilan_harfler) * 100)

        for i, h in enumerate(cevap):
            if h == " ":
                self.kelime_box.add_widget(Label(size_hint=(None, None), size=(bosluk_w, dp(54))))
            elif h in noktalama:
                lbl = Label(
                    text=h,
                    size_hint=(None, None),
                    size=(nokta_w, dp(54)),
                    font_size='24sp',
                    bold=True,
                    color=(1, 0.8, 0, 1)
                )
                self.kelime_box.add_widget(lbl)
            else:
                acik = i in self.acilan_harfler
                lbl = Label(
                    text=h if acik else " ",
                    size_hint=(None, None),
                    size=(kutu_genisligi, dp(54)),
                    font_size=f_size,
                    bold=True,
                    color=(1, 1, 1, 1)
                )
                lbl.acik = acik
                lbl.bind(pos=self._redraw_box, size=self._redraw_box)
                self._redraw_box(lbl, None)
                self.kelime_box.add_widget(lbl)

    def _redraw_box(self, inst, val):
        inst.canvas.before.clear()
        with inst.canvas.before:
            if getattr(inst, 'acik', False):
                Color(0.2, 0.17, 0.04, 0.97)
            else:
                Color(0.08, 0.08, 0.1, 0.95)
            RoundedRectangle(size=inst.size, pos=inst.pos, radius=[dp(8)])
            Color(1, 0.8, 0, 1)
            Line(rounded_rectangle=(inst.x, inst.y, inst.width, inst.height, dp(8)), width=1.5)

    # ------------------------------------------------------------ OYUN AKIŞI
    def soru_gec(self, instance):
        if not self.oyun_aktif or self.benjamin_aktif or self.animasyon_aktif or self.duraklatildi:
            return
        if self.gec_hakki > 0:
            self.gec_hakki -= 1
            self.yanlis_cevaplananlar.append({
                "soru": self.mevcut_soru["soru"],
                "cevap": self.mevcut_soru["cevap"],
                "durum": "PAS GEÇİLDİ"
            })
            self.ses_cal('yanlis_cevap.mp3')
            self.btn_gec.metin_guncelle(f"GEÇ ({self.gec_hakki})")
            if self.gec_hakki == 0:
                self.btn_gec.disabled = True
            self.sonraki_soru()

    def harf_al(self, instance):
        if not self.oyun_aktif or self.benjamin_aktif or self.animasyon_aktif or self.duraklatildi:
            return
        self.ses_cal('harf.mp3')
        cevap = self.mevcut_soru["cevap"]
        harfler = [i for i, h in enumerate(cevap) if h not in (" ", ".", ",", "-")]

        if len(self.acilan_harfler) < len(harfler) - 1:
            kalan = [i for i in harfler if i not in self.acilan_harfler]
            if kalan:
                self.acilan_harfler.append(random.choice(kalan))
                self.kelime_guncelle()

    def benjamin_ac(self, instance):
        if not self.oyun_aktif or self.benjamin_aktif or self.animasyon_aktif or self.duraklatildi:
            return
        self.benjamin_aktif = True
        self.benjamin_sure = BENJAMIN_SURESI
        self.ses_cal('benjamin.mp3')

        if self.alt_butonlar_kutusu in self.layout.children:
            self.layout.remove_widget(self.alt_butonlar_kutusu)
        if self.tahmin_kutusu not in self.layout.children:
            self.layout.add_widget(self.tahmin_kutusu)
        if self.klavye_container not in self.layout.children:
            self.layout.add_widget(self.klavye_container)

        self.girilen_tahmin = ""
        self.tahmin_kutusu.text = "KLAVYEDEN YAZIN..."

        if self.benjamin_event:
            Clock.unschedule(self.benjamin_event)
        self.benjamin_event = Clock.schedule_interval(self.benjamin_timer_tick, 1)
        self.bilgi_guncelle()

    def benjamin_timer_tick(self, dt):
        if self.duraklatildi or self.animasyon_aktif:
            return
        self.benjamin_sure -= 1
        self.bilgi_guncelle()
        if self.benjamin_sure <= 0:
            self.cevap_kontrol(None)

    def kilitleri_ac(self):
        if self.tahmin_kutusu in self.layout.children:
            self.layout.remove_widget(self.tahmin_kutusu)
        if self.klavye_container in self.layout.children:
            self.layout.remove_widget(self.klavye_container)

        if self.alt_butonlar_kutusu not in self.layout.children:
            self.layout.add_widget(self.alt_butonlar_kutusu)

        self.btn_harf.disabled = False
        self.btn_benjamin.disabled = False
        self.btn_gec.disabled = self.gec_hakki <= 0
        self.benjamin_aktif = False
        self.bilgi_guncelle()

    def cevap_kontrol(self, instance):
        # Çift tıklama / animasyon sırasında tekrar puan yazılmasını engelle
        if not self.oyun_aktif or not self.benjamin_aktif or self.animasyon_aktif or self.duraklatildi:
            return

        if self.benjamin_event:
            Clock.unschedule(self.benjamin_event)
            self.benjamin_event = None

        girilen_norm = normalize_karsilastir(self.girilen_tahmin)
        dogru_norm = normalize_karsilastir(self.mevcut_soru["cevap"])

        if girilen_norm == dogru_norm and girilen_norm != "":
            self.ses_cal('dogru.mp3')

            final_puan = self.mevcut_soru_degeri
            if not self.acilan_harfler:
                final_puan *= 2
                self.ucan_efekt("KOMBO! x2", (1, 0.8, 0, 1))
            else:
                self.ucan_efekt(f"+{final_puan}", (0, 1, 0, 1))
            self.puan += final_puan
            self.bilgi_guncelle()
            self.harfleri_sirayla_ac()
            self.show_feedback(True)
        else:
            self.yanlis_cevaplananlar.append({
                "soru": self.mevcut_soru["soru"],
                "cevap": self.mevcut_soru["cevap"],
                "durum": "YANLIŞ CEVAP"
            })
            self.ses_cal('yanlis_cevap.mp3')
            self.puan -= self.mevcut_soru_degeri
            self.ucan_efekt(f"-{self.mevcut_soru_degeri}", (1, 0.3, 0.3, 1))
            self.show_feedback(False)
            self.kilitleri_ac()
            self.sonraki_soru()

    def ucan_efekt(self, metin, renk):
        Animation.cancel_all(self.efekt_label)
        self.efekt_label.pos_hint = {'center_x': 0.5, 'center_y': 0.64}
        self.efekt_label.text = metin
        self.efekt_label.color = renk
        self.efekt_label.opacity = 1
        Animation(pos_hint={'center_x': 0.5, 'center_y': 0.74}, opacity=0, duration=1.2).start(self.efekt_label)

    def harfleri_sirayla_ac(self):
        self.animasyon_aktif = True
        cevap = self.mevcut_soru["cevap"]
        harf_indeksleri = [i for i, h in enumerate(cevap) if h not in (" ", ".", ",", "-")]
        for i, idx in enumerate(harf_indeksleri):
            Clock.schedule_once(lambda dt, index=idx: self._tek_harf_ac(index), i * 0.08)
        Clock.schedule_once(self.animasyon_bitir, len(harf_indeksleri) * 0.08 + 1)

    def animasyon_bitir(self, dt):
        if not self.oyun_aktif:
            return
        self.animasyon_aktif = False
        self.kilitleri_ac()
        self.sonraki_soru()

    def _tek_harf_ac(self, index):
        if not self.oyun_aktif:
            return
        if index not in self.acilan_harfler:
            self.acilan_harfler.append(index)
            self.kelime_guncelle()

    def timer_guncelle(self, dt):
        if not self.oyun_aktif or self.duraklatildi or self.benjamin_aktif:
            return
        if self.sure > 0:
            self.sure -= 1
            self.bilgi_guncelle()
            if self.sure == 10 and not self.geri_sayim_caldi:
                self.geri_sayim_caldi = True
                self.ses_cal('geri_sayim.mp3')
        if self.sure <= 0:
            self.oyun_bitti("SÜRE DOLDU!")

    def oyunu_sifirla(self):
        self.puan, self.sure, self.soru_sirasi = 0, OYUN_SURESI, 0
        self.gec_hakki = GEC_HAKKI
        self.geri_sayim_caldi = False
        self.animasyon_aktif = False
        self.duraklatildi = False
        self.benjamin_aktif = False
        if self.benjamin_event:
            Clock.unschedule(self.benjamin_event)
            self.benjamin_event = None
        self.yanlis_cevaplananlar.clear()
        self.btn_gec.metin_guncelle(f"GEÇ ({self.gec_hakki})")

        # Her yeni oyunda soruları yeniden yükle ve karıştır
        self.soru_listesi = self.sorulari_yukle()

        self.kilitleri_ac()
        self.oyun_aktif = True

        if self.bg_music and self.ses_durumu and self.bg_music.state != 'play':
            self.bg_music.play()

        self.bilgi_guncelle()
        self.soru_yukle()

    def soru_yukle(self):
        if not self.soru_listesi:
            self.oyun_aktif = False
            self.soru_label.text = "Soru dosyası bulunamadı (sorular.txt)"
            return

        if self.soru_sirasi < len(self.soru_listesi):
            self.mevcut_soru = self.soru_listesi[self.soru_sirasi]
            self.acilan_harfler = []
            metin = self.mevcut_soru["soru"]
            self.soru_label.text = metin
            if len(metin) > 110:
                self.soru_label.font_size = '13sp'
            elif len(metin) > 70:
                self.soru_label.font_size = '14.5sp'
            else:
                self.soru_label.font_size = '16sp'
            self.seviye_guncelle(sira_seviyesi(self.soru_sirasi))
            self.kelime_guncelle()
        else:
            self.oyun_bitti("TEBRİKLER!")

    def sonraki_soru(self):
        self.soru_sirasi += 1
        self.soru_yukle()

    def show_feedback(self, success):
        hedef_gorsel = 'dogru.png' if success else 'yanlis.png'
        if dosya_var(hedef_gorsel):
            self.feedback_img.source = yol(hedef_gorsel)
            self.feedback_img.opacity = 1
            Clock.schedule_once(lambda dt: setattr(self.feedback_img, 'opacity', 0), 0.8)

    # ------------------------------------------------------------ ÇIKIŞ / GERİ
    def cikis_sor(self):
        """Android geri tuşu: oyundan çıkmak istiyor musun?"""
        if not self.oyun_aktif or self.cikis_popup is not None:
            return
        self.duraklatildi = True

        kutu = BoxLayout(orientation='vertical', padding=dp(14), spacing=dp(12))
        kutu.add_widget(Label(text="Oyundan çıkıp ana menüye\ndönmek istiyor musun?\n(Bu oyunun skoru kaydedilmez)",
                              halign='center', font_size='15sp'))
        satir = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(10))
        btn_hayir = YuvarlakButon(text="DEVAM ET", renk=YESIL, bold=True, font_size='15sp')
        btn_evet = YuvarlakButon(text="ÇIK", renk=KIRMIZI, bold=True, font_size='15sp')
        satir.add_widget(btn_hayir)
        satir.add_widget(btn_evet)
        kutu.add_widget(satir)

        self.cikis_popup = popup_yap('DURAKLATILDI', kutu, (0.85, 0.34), kapanabilir=False)

        def devam(*a):
            self.cikis_popup.dismiss()
            self.cikis_popup = None
            self.duraklatildi = False

        def cik(*a):
            self.cikis_popup.dismiss()
            self.cikis_popup = None
            self.menuye_don()

        btn_hayir.bind(on_release=devam)
        btn_evet.bind(on_release=cik)
        self.cikis_popup.open()

    def menuye_don(self):
        self.oyun_aktif = False
        self.duraklatildi = False
        self.animasyon_aktif = False
        self.benjamin_aktif = False
        if self.benjamin_event:
            Clock.unschedule(self.benjamin_event)
            self.benjamin_event = None
        self.manager.current = 'giris'

    # ------------------------------------------------------------ OYUN SONU
    def oyun_bitti(self, mesaj):
        if not self.oyun_aktif:
            return
        self.oyun_aktif = False
        self.benjamin_aktif = False
        if self.benjamin_event:
            Clock.unschedule(self.benjamin_event)
            self.benjamin_event = None

        if self.bg_music:
            self.bg_music.stop()
        if mesaj == "SÜRE DOLDU!":
            self.ses_cal('sure_bitimi.mp3')

        # Süre bittiği anda cevaplanmamış olan soruyu listeye ekle
        if mesaj == "SÜRE DOLDU!" and self.mevcut_soru:
            zaten_var = any(item["soru"] == self.mevcut_soru["soru"] for item in self.yanlis_cevaplananlar)
            if not zaten_var:
                self.yanlis_cevaplananlar.append({
                    "soru": self.mevcut_soru["soru"],
                    "cevap": self.mevcut_soru["cevap"],
                    "durum": "SÜRE YETMEDİ"
                })

        yeni_rekor = skor_kaydet(self.puan)

        ana_kutu = BoxLayout(orientation='vertical', padding=dp(16), spacing=dp(10))

        rekor_yazi = "\n[color=33ff77]YENİ REKOR![/color]" if yeni_rekor else ""
        lbl_skor = Label(
            text=f"{mesaj}\nTOPLAM SKORUNUZ: {self.puan}{rekor_yazi}",
            markup=True,
            font_size='21sp',
            bold=True,
            color=(1, 0.85, 0.2, 1),
            halign='center'
        )
        ana_kutu.add_widget(lbl_skor)

        if self.yanlis_cevaplananlar:
            btn_cevaplar = YuvarlakButon(
                text=f"DOĞRU CEVAPLARI GÖR ({len(self.yanlis_cevaplananlar)} Soru)",
                size_hint=(1, None),
                height=dp(50),
                renk=(0.18, 0.5, 0.8, 1),
                bold=True,
                font_size='15sp'
            )
            btn_cevaplar.bind(on_release=lambda x: [popup_bitti.dismiss(), self.reklam_izlet_ve_cevaplari_goster()])
            ana_kutu.add_widget(btn_cevaplar)
        else:
            lbl_kusursuz = Label(
                text="Harika! Hiç yanlışınız veya pasınız yok, tebrikler!",
                font_size='14sp',
                bold=True,
                color=(0.2, 0.9, 0.4, 1),
                size_hint_y=None,
                height=dp(30)
            )
            ana_kutu.add_widget(lbl_kusursuz)

        btn_yeniden = YuvarlakButon(
            text="YENİDEN OYNA",
            size_hint=(1, None),
            height=dp(50),
            renk=(0, 0.7, 0.3, 1),
            bold=True,
            font_size='16sp'
        )
        btn_yeniden.bind(on_release=lambda x: [popup_bitti.dismiss(), self.oyunu_sifirla()])
        ana_kutu.add_widget(btn_yeniden)

        btn_menu = YuvarlakButon(
            text="ANA MENÜ",
            size_hint=(1, None),
            height=dp(46),
            renk=(0.25, 0.28, 0.38, 1),
            bold=True,
            font_size='15sp'
        )
        btn_menu.bind(on_release=lambda x: [popup_bitti.dismiss(), self.menuye_don()])
        ana_kutu.add_widget(btn_menu)

        popup_bitti = popup_yap('OYUN BİTTİ', ana_kutu, (0.9, 0.58), kapanabilir=False)
        popup_bitti.open()

    def reklam_izlet_ve_cevaplari_goster(self):
        app = App.get_running_app()
        if hasattr(app, 'ads') and app.ads:
            try:
                if app.ads.is_interstitial_loaded():
                    app.ads.show_interstitial()
                    app.ads.request_interstitial()
            except Exception:
                pass

        self.dogru_cevaplari_listele_popup()

    def dogru_cevaplari_listele_popup(self):
        ana_kutu = BoxLayout(orientation='vertical', padding=dp(12), spacing=dp(10))

        scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False)
        liste_kutu = BoxLayout(orientation='vertical', spacing=dp(8), size_hint_y=None)
        liste_kutu.bind(minimum_height=liste_kutu.setter('height'))

        durum_renkleri = {
            "YANLIŞ CEVAP": (1, 0.4, 0.4, 1),
            "PAS GEÇİLDİ": (1, 0.8, 0.2, 1),
            "SÜRE YETMEDİ": (0.6, 0.7, 1, 1),
        }

        for idx, item in enumerate(self.yanlis_cevaplananlar, start=1):
            soru_karti = BoxLayout(orientation='vertical', spacing=dp(2), size_hint_y=None,
                                   height=dp(92), padding=[dp(10), dp(6)])
            soru_karti.bind(pos=lambda inst, val: self._kart_ciz(inst), size=lambda inst, val: self._kart_ciz(inst))

            lbl_s = Label(
                text=f"{idx}. {item['soru']}",
                font_size='13sp',
                bold=True,
                halign='left',
                valign='middle',
                color=(1, 1, 1, 1)
            )
            lbl_s.bind(size=lbl_s.setter('text_size'))
            soru_karti.add_widget(lbl_s)

            lbl_c = Label(
                text=f"Doğru Cevap: {item['cevap']}",
                font_size='15sp',
                bold=True,
                halign='left',
                valign='middle',
                color=(0.15, 0.85, 0.45, 1)
            )
            lbl_c.bind(size=lbl_c.setter('text_size'))
            soru_karti.add_widget(lbl_c)

            lbl_d = Label(
                text=item['durum'],
                font_size='11sp',
                bold=True,
                halign='left',
                valign='middle',
                size_hint_y=None,
                height=dp(16),
                color=durum_renkleri.get(item['durum'], (0.8, 0.8, 0.8, 1))
            )
            lbl_d.bind(size=lbl_d.setter('text_size'))
            soru_karti.add_widget(lbl_d)

            liste_kutu.add_widget(soru_karti)

        scroll.add_widget(liste_kutu)
        ana_kutu.add_widget(scroll)

        btn_kapat = YuvarlakButon(
            text="YENİDEN OYNA",
            size_hint=(1, None),
            height=dp(46),
            renk=(0, 0.7, 0.3, 1),
            bold=True,
            font_size='16sp'
        )
        btn_kapat.bind(on_release=lambda x: [popup_detay.dismiss(), self.oyunu_sifirla()])
        ana_kutu.add_widget(btn_kapat)

        btn_menu = YuvarlakButon(
            text="ANA MENÜ",
            size_hint=(1, None),
            height=dp(42),
            renk=(0.25, 0.28, 0.38, 1),
            bold=True,
            font_size='14sp'
        )
        btn_menu.bind(on_release=lambda x: [popup_detay.dismiss(), self.menuye_don()])
        ana_kutu.add_widget(btn_menu)

        popup_detay = popup_yap('Yanıtlanamayan Soruların Doğruları', ana_kutu, (0.94, 0.85), kapanabilir=False)
        popup_detay.open()

    def _kart_ciz(self, inst):
        inst.canvas.before.clear()
        with inst.canvas.before:
            Color(0.12, 0.14, 0.18, 0.95)
            RoundedRectangle(pos=inst.pos, size=inst.size, radius=[dp(8)])
            Color(0.3, 0.35, 0.45, 0.5)
            Line(rounded_rectangle=(inst.x, inst.y, inst.width, inst.height, dp(8)), width=1)

    def sorulari_yukle(self):
        """sorular.txt okur. Satır biçimi:  seviye|soru,cevap   (seviye 1-4)
        Seviyesiz satırlar da çalışır; seviye cevap uzunluğuna göre tahmin edilir."""
        havuz = {1: [], 2: [], 3: [], 4: []}
        dosya = yol("sorular.txt")
        if os.path.exists(dosya):
            with open(dosya, "r", encoding="utf-8-sig") as f:
                for s in f:
                    s = s.strip()
                    seviye = None
                    m = re.match(r'^([1-4])\s*\|\s*(.*)$', s)
                    if m:
                        seviye = int(m.group(1))
                        s = m.group(2).strip()
                    if "," in s:
                        q, a = s.split(",", 1)
                        if q.strip() and a.strip():
                            if seviye is None:
                                seviye = seviye_tahmin_et(a.strip())
                            havuz[seviye].append({"soru": q.strip(), "cevap": a.strip()})

        for liste in havuz.values():
            random.shuffle(liste)

        def cek(seviye, adet):
            alinan = havuz[seviye][:adet]
            del havuz[seviye][:adet]
            # Bu seviyede yeterli soru yoksa komşu seviyelerden tamamla
            if len(alinan) < adet:
                diger = [k for k in range(seviye + 1, 5)] + [k for k in range(seviye - 1, 0, -1)]
                for k in diger:
                    eksik = adet - len(alinan)
                    if eksik <= 0:
                        break
                    alinan += havuz[k][:eksik]
                    del havuz[k][:eksik]
            return alinan

        sirali = []
        for seviye, adet in SEVIYE_PLANI:
            sirali += cek(seviye, adet)

        # Plandan sonra: önce tüm "çok zor" sorular, ardından kalanlar (zordan kolaya)
        for k in (4, 3, 2, 1):
            sirali += havuz[k]
        return sirali


# ---------------------------------------------------------------------------
# UYGULAMA
# ---------------------------------------------------------------------------
class KelimeApp(App):
    def build(self):
        self.title = "Kelime Avcıları"
        if dosya_var('icon.png'):
            self.icon = yol('icon.png')

        self.ads = None
        if platform == 'android':
            gecis_id = ADMOB_TEST_GECIS_ID if REKLAM_TEST_MODU else ADMOB_GERCEK_GECIS_ID
            try:
                self.ads = YerelReklam(gecis_id)
            except Exception:
                self.ads = None
                if KivMob:
                    try:
                        self.ads = KivMob(ADMOB_APP_ID)
                        self.ads.new_interstitial(gecis_id)
                        self.ads.request_interstitial()
                    except Exception:
                        self.ads = None

        Window.bind(on_keyboard=self.geri_tusu)

        sm = ScreenManager(transition=FadeTransition(duration=0.3))
        sm.add_widget(GirisEkrani(name='giris'))
        sm.add_widget(OyunEkrani(name='oyun'))
        return sm

    def geri_tusu(self, window, key, *args):
        # 27 = Android geri tuşu / ESC
        if key == 27:
            if self.root.current == 'oyun':
                self.root.get_screen('oyun').cikis_sor()
                return True
            return False  # Ana menüdeyken uygulamadan çıkar
        return False

    def on_pause(self):
        oyun_ekrani = self.root.get_screen('oyun')
        if oyun_ekrani and oyun_ekrani.bg_music:
            if oyun_ekrani.bg_music.state == 'play':
                oyun_ekrani.bg_music.stop()
        if oyun_ekrani and oyun_ekrani.oyun_aktif:
            oyun_ekrani.duraklatildi = True
        return True

    def on_resume(self):
        oyun_ekrani = self.root.get_screen('oyun')
        if not oyun_ekrani:
            return
        if self.root.current == 'oyun' and oyun_ekrani.oyun_aktif:
            if oyun_ekrani.cikis_popup is None:
                oyun_ekrani.duraklatildi = False
            if oyun_ekrani.bg_music and oyun_ekrani.ses_durumu:
                oyun_ekrani.bg_music.play()


if __name__ == '__main__':
    KelimeApp().run()
