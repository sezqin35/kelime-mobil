import random
import os
import re
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
from kivy.utils import get_color_from_hex
from kivy.graphics import Color, Rectangle, Line, RoundedRectangle
from kivy.animation import Animation
from kivy.utils import platform

# PC üzerinde dikey mobil telefon boyutunda başlat
if platform not in ('android', 'ios'):
    Window.size = (420, 750)

# Android Klavye Modu
Window.softinput_mode = 'pan'

# AdMob Entegrasyonu
if platform == 'android':
    try:
        from kivmob import KivMob
    except ImportError:
        KivMob = None
else:
    KivMob = None


def turkce_buyut(metin):
    donusum = {
        'i': 'İ', 'ı': 'I', 'ş': 'Ş', 'ğ': 'Ğ', 
        'ü': 'Ü', 'ö': 'Ö', 'ç': 'Ç'
    }
    return "".join(donusum.get(k, k.upper()) for k in metin).strip()


def normalize_karsilastir(metin):
    buyuk = turkce_buyut(metin)
    return re.sub(r'[\s\.\,\-\'\"]+', '', buyuk)


class SadeMuzikButonu(Button):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.ses_acik = True
        self.background_color = (0, 0, 0, 0)
        self.background_normal = ''
        
        self.img = Image(allow_stretch=True, keep_ratio=True)
        self.add_widget(self.img)

        self.lbl = Label(font_size='12sp', bold=True)
        self.add_widget(self.lbl)

        self.bind(pos=self._guncelle, size=self._guncelle)
        self.durum_guncelle(True)

    def _guncelle(self, *args):
        self.img.size = self.size
        self.img.pos = self.pos
        self.lbl.size = self.size
        self.lbl.pos = self.pos

        if not (os.path.exists('muzik_acik.png') and os.path.exists('muzik_kapali.png')):
            self.canvas.before.clear()
            with self.canvas.before:
                if self.ses_acik:
                    Color(0.1, 0.6, 0.35, 0.85)
                else:
                    Color(0.3, 0.3, 0.35, 0.75)
                RoundedRectangle(pos=self.pos, size=self.size, radius=[8])
                Color(1, 1, 1, 0.4)
                Line(rounded_rectangle=(self.x, self.y, self.width, self.height, 8), width=1)

    def durum_guncelle(self, acik):
        self.ses_acik = acik
        has_png = os.path.exists('muzik_acik.png') and os.path.exists('muzik_kapali.png')

        if has_png:
            self.img.opacity = 1
            self.lbl.opacity = 0
            self.img.source = 'muzik_acik.png' if acik else 'muzik_kapali.png'
            self.canvas.before.clear()
        else:
            self.img.opacity = 0
            self.lbl.opacity = 1
            self.lbl.text = "SES: AÇIK" if acik else "SES: KAPALI"
            self.lbl.color = (1, 1, 1, 1) if acik else (0.85, 0.85, 0.85, 0.9)
            self._guncelle()


class ResimliButon(Button):
    def __init__(self, resim_yolu, alt_yazi="", **kwargs):
        super().__init__(**kwargs)
        self.background_color = (0, 0, 0, 0)
        self.background_normal = ''
        self.resim_yolu = resim_yolu
        self.alt_yazi = alt_yazi

        self.img = Image(
            source=self.resim_yolu, 
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
        self.bind(pos=self._yerlesim_guncelle, size=self._yerlesim_guncelle)

    def _yerlesim_guncelle(self, *args):
        self.img.size = (self.width, self.height * 0.75)
        self.img.pos = (self.x, self.y + self.height * 0.22)
        
        self.lbl.size = (self.width, self.height * 0.25)
        self.lbl.pos = (self.x, self.y)

    def metin_guncelle(self, yeni_metin):
        self.lbl.text = yeni_metin


class GirisEkrani(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = FloatLayout()
        
        if os.path.exists('Kelime_oyunu.png'):
            layout.add_widget(Image(source='Kelime_oyunu.png', allow_stretch=True, keep_ratio=False, size_hint=(1, 1)))
        
        btn_basla = Button(
            text="BAŞLA", 
            size_hint=(0.65, 0.08), 
            pos_hint={'center_x': 0.5, 'y': 0.22},
            background_color=(0, 0.8, 0.2, 1), 
            font_size='24sp', 
            bold=True, 
            background_normal=''
        )
        btn_basla.bind(on_release=self.basla)
        layout.add_widget(btn_basla)

        btn_skor = Button(
            text="EN YÜKSEK SKORLAR", 
            size_hint=(0.65, 0.065), 
            pos_hint={'center_x': 0.5, 'y': 0.13},
            background_color=(0.1, 0.5, 0.8, 1), 
            font_size='16sp', 
            bold=True, 
            background_normal=''
        )
        btn_skor.bind(on_release=self.skorlari_goster)
        layout.add_widget(btn_skor)
        self.add_widget(layout)

    def basla(self, instance):
        self.manager.current = 'oyun'

    def skorlari_goster(self, instance):
        App.get_running_app().root.get_screen('oyun').skor_tablosu_popup()


class OyunEkrani(Screen):
    def on_enter(self):
        self.oyunu_sifirla()
        if self.bg_music and self.ses_durumu:
            self.bg_music.play()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = FloatLayout()
        self.add_widget(self.layout)
        
        self.puan, self.sure, self.ses_durumu, self.oyun_aktif = 0, 120, True, True
        self.acilan_harfler = []
        self.benjamin_aktif = False
        self.animasyon_aktif = False
        self.gec_hakki = 3
        self.benjamin_event = None
        self.girilen_tahmin = ""
        self.yanlis_cevaplananlar = []
        
        self.ses_havuzu = {}
        self._sesleri_yukle()
        
        if os.path.exists('studyo.png'):
            self.layout.add_widget(Image(source='studyo.png', allow_stretch=True, keep_ratio=False, size_hint=(1, 1)))
        
        self.ust_panel_bg = Label(size_hint=(1, 0.08), pos_hint={'top': 1})
        with self.ust_panel_bg.canvas.before:
            Color(0.05, 0.05, 0.08, 0.95)
            self.rect_bg = Rectangle(size=self.ust_panel_bg.size, pos=self.ust_panel_bg.pos)
        self.ust_panel_bg.bind(pos=self._update_panel_rect, size=self._update_panel_rect)
        self.layout.add_widget(self.ust_panel_bg)

        self.btn_ses = SadeMuzikButonu(
            size_hint=(None, None), 
            size=(105, 34),
            pos_hint={'right': 0.98, 'top': 0.99}
        )
        self.btn_ses.bind(on_release=self.ses_degistir)
        self.layout.add_widget(self.btn_ses)

        self.bilgi_label = Label(
            text="", 
            font_size='18sp', 
            bold=True, 
            color=(1, 1, 1, 1),
            pos_hint={'center_x': 0.40, 'top': 0.99}, 
            size_hint=(0.60, 0.06)
        )
        self.layout.add_widget(self.bilgi_label)

        self.soru_container = BoxLayout(size_hint=(0.92, 0.13), pos_hint={'center_x': 0.5, 'center_y': 0.72})
        with self.soru_container.canvas.before:
            Color(0, 0, 0, 0.82)
            self.soru_bg = RoundedRectangle(size=self.soru_container.size, pos=self.soru_container.pos, radius=[12])
            Color(0.9, 0.7, 0.1, 0.8)
            self.soru_border = Line(rounded_rectangle=(self.soru_container.x, self.soru_container.y, self.soru_container.width, self.soru_container.height, 12), width=1.2)
        
        self.soru_container.bind(pos=self._update_soru_bg, size=self._update_soru_bg)
        
        self.soru_label = Label(text="", halign='center', valign='middle', font_size='16sp', bold=True)
        self.soru_label.bind(size=self.soru_label.setter('text_size'))
        self.soru_container.add_widget(self.soru_label)
        self.layout.add_widget(self.soru_container)

        self.kelime_box = GridLayout(
            rows=1, 
            spacing=4, 
            size_hint=(None, None), 
            height=60, 
            pos_hint={'center_x': 0.5, 'center_y': 0.58}
        )
        self.layout.add_widget(self.kelime_box)

        self.alt_butonlar_kutusu = BoxLayout(
            size_hint=(0.94, 0.12), 
            pos_hint={'center_x': 0.5, 'y': 0.03}, 
            spacing=12
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
            alt_yazi='GEÇ (3)', 
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
            self.tahmin_bg_rect = RoundedRectangle(size=self.tahmin_kutusu.size, pos=self.tahmin_kutusu.pos, radius=[10])
            Color(1, 0.8, 0, 1)
            self.tahmin_line = Line(rounded_rectangle=(self.tahmin_kutusu.x, self.tahmin_kutusu.y, self.tahmin_kutusu.width, self.tahmin_kutusu.height, 10), width=1.5)
        self.tahmin_kutusu.bind(pos=self._update_tahmin_rect, size=self._update_tahmin_rect)

        self.klavye_container = BoxLayout(
            orientation='vertical',
            size_hint=(0.98, 0.36),
            pos_hint={'center_x': 0.5, 'y': 0.01},
            spacing=3
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

    def _sesleri_yukle(self):
        ses_dosyalari = ['dogru.mp3', 'yanlis_cevap.mp3', 'harf.mp3', 'benjamin.mp3', 'ses.mp3']
        for s_adi in ses_dosyalari:
            hedef_dosya = None
            if os.path.exists(s_adi):
                hedef_dosya = s_adi
            else:
                for dosya in os.listdir('.'):
                    if dosya.lower().strip() == s_adi.lower().strip():
                        hedef_dosya = dosya
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
        if not s:
            if os.path.exists(dosya_adi):
                s = SoundLoader.load(dosya_adi)
                if s:
                    self.ses_havuzu[dosya_adi] = s

        if s:
            try:
                s.stop()
                s.volume = 1.0
                s.play()
            except Exception:
                pass

    def _sanal_klavyeyi_olustur(self):
        rakamlar = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"]
        rakam_kutusu = BoxLayout(spacing=2, size_hint_y=0.18)
        for r in rakamlar:
            b = Button(
                text=r, 
                font_size='15sp', 
                bold=True, 
                background_color=(0.18, 0.22, 0.28, 1), 
                background_normal=''
            )
            b.bind(on_release=lambda x, val=r: self.klavye_tus_basildi(val))
            rakam_kutusu.add_widget(b)
        self.klavye_container.add_widget(rakam_kutusu)

        harf_satirlari = [
            ["Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P", "Ğ", "Ü"],
            ["A", "S", "D", "F", "G", "H", "J", "K", "L", "Ş", "İ"],
            ["Z", "X", "C", "V", "B", "N", "M", "Ö", "Ç"]
        ]
        
        for satir in harf_satirlari:
            satir_kutu = BoxLayout(spacing=2, size_hint_y=0.20)
            for harf in satir:
                b = Button(
                    text=harf, 
                    font_size='16sp', 
                    bold=True, 
                    background_color=(0.25, 0.28, 0.35, 1), 
                    background_normal=''
                )
                b.bind(on_release=lambda x, h=harf: self.klavye_tus_basildi(h))
                satir_kutu.add_widget(b)
            self.klavye_container.add_widget(satir_kutu)

        alt_kutu = BoxLayout(spacing=4, size_hint_y=0.22)
        
        btn_sil = Button(
            text="SİL", 
            size_hint=(0.20, 1), 
            background_color=(0.7, 0.2, 0.2, 1), 
            bold=True, 
            font_size='15sp',
            background_normal=''
        )
        btn_sil.bind(on_release=self.klavye_sil)
        alt_kutu.add_widget(btn_sil)

        btn_nokta = Button(
            text=".", 
            size_hint=(0.15, 1), 
            background_color=(0.3, 0.35, 0.45, 1), 
            bold=True, 
            font_size='22sp',
            background_normal=''
        )
        btn_nokta.bind(on_release=lambda x: self.klavye_tus_basildi("."))
        alt_kutu.add_widget(btn_nokta)

        btn_bosluk = Button(
            text="BOŞLUK", 
            size_hint=(0.35, 1), 
            background_color=(0.2, 0.4, 0.55, 1), 
            bold=True, 
            font_size='14sp',
            background_normal=''
        )
        btn_bosluk.bind(on_release=lambda x: self.klavye_tus_basildi(" "))
        alt_kutu.add_widget(btn_bosluk)

        btn_onay = Button(
            text="GÖNDER", 
            size_hint=(0.30, 1), 
            background_color=(0.12, 0.7, 0.3, 1), 
            bold=True, 
            font_size='15sp',
            background_normal=''
        )
        btn_onay.bind(on_release=lambda x: self.cevap_kontrol(None))
        alt_kutu.add_widget(btn_onay)

        self.klavye_container.add_widget(alt_kutu)

    def klavye_tus_basildi(self, karakter):
        if not self.benjamin_aktif:
            return
        self.girilen_tahmin += karakter
        self.tahmin_kutusu.text = self.girilen_tahmin

    def klavye_sil(self, instance):
        if not self.benjamin_aktif:
            return
        self.girilen_tahmin = self.girilen_tahmin[:-1]
        self.tahmin_kutusu.text = self.girilen_tahmin if self.girilen_tahmin else "..."

    def _update_tahmin_rect(self, inst, val):
        self.tahmin_bg_rect.pos = inst.pos
        self.tahmin_bg_rect.size = inst.size
        self.tahmin_line.rounded_rectangle = (inst.x, inst.y, inst.width, inst.height, 10)

    def ses_degistir(self, instance):
        self.ses_durumu = not self.ses_durumu
        self.btn_ses.durum_guncelle(self.ses_durumu)

        if self.ses_durumu:
            if self.bg_music:
                self.bg_music.play()
        else:
            if self.bg_music:
                self.bg_music.stop()

    def _update_panel_rect(self, instance, value):
        self.rect_bg.pos = instance.pos
        self.rect_bg.size = instance.size

    def _update_soru_bg(self, instance, value):
        self.soru_bg.pos = instance.pos
        self.soru_bg.size = instance.size
        self.soru_border.rounded_rectangle = (instance.x, instance.y, instance.width, instance.height, 12)

    def kelime_guncelle(self):
        self.kelime_box.clear_widgets()
        if not hasattr(self, 'mevcut_soru') or not self.mevcut_soru:
            return

        cevap = self.mevcut_soru["cevap"]
        harf_sayisi = len(cevap)
        if harf_sayisi == 0:
            return

        total_width = Window.width * 0.94
        kutu_genisligi = max(24, (total_width / harf_sayisi) - 4)
        self.kelime_box.width = (kutu_genisligi + 4) * harf_sayisi
        f_size = '20sp' if harf_sayisi > 9 else ('24sp' if harf_sayisi > 6 else '30sp')
        
        cevap_temiz = re.sub(r'[\s\.\,\-]+', '', cevap)
        self.mevcut_soru_degeri = (len(cevap_temiz) * 100) - (len(self.acilan_harfler) * 100)

        for i, h in enumerate(cevap):
            if h == " ":
                self.kelime_box.add_widget(Label(size_hint_x=None, width=10))
            elif h in (".", ",", "-"):
                lbl = Label(
                    text=h, 
                    size_hint=(None, None), 
                    size=(16, 60), 
                    font_size='24sp', 
                    bold=True, 
                    color=(1, 0.8, 0, 1)
                )
                self.kelime_box.add_widget(lbl)
            else:
                txt = h if i in self.acilan_harfler else " "
                lbl = Label(
                    text=txt, 
                    size_hint=(None, None), 
                    size=(kutu_genisligi, 60), 
                    font_size=f_size, 
                    bold=True, 
                    color=(1, 1, 1, 1)
                )
                with lbl.canvas.before:
                    Color(0.08, 0.08, 0.1, 0.95)
                    Rectangle(size=lbl.size, pos=lbl.pos)
                    Color(1, 0.8, 0, 1)
                    Line(rounded_rectangle=(lbl.x, lbl.y, lbl.width, lbl.height, 8), width=1.5)
                lbl.bind(pos=self._redraw_box, size=self._redraw_box)
                self.kelime_box.add_widget(lbl)

    def _redraw_box(self, inst, val):
        inst.canvas.before.clear()
        with inst.canvas.before:
            Color(0.08, 0.08, 0.1, 0.95)
            Rectangle(size=inst.size, pos=inst.pos)
            Color(1, 0.8, 0, 1)
            Line(rounded_rectangle=(inst.x, inst.y, inst.width, inst.height, 8), width=1.5)

    def soru_gec(self, instance):
        if not self.oyun_aktif or self.benjamin_aktif or self.animasyon_aktif:
            return
        if self.gec_hakki > 0:
            self.gec_hakki -= 1
            self.yanlis_cevaplananlar.append({
                "soru": self.mevcut_soru["soru"],
                "cevap": self.mevcut_soru["cevap"],
                "durum": "PAS GEÇİLDİ"
            })
            self.ses_cal('yanlis_cevap.mp3')
            self.sonraki_soru()
            self.btn_gec.metin_guncelle(f"GEÇ ({self.gec_hakki})")
            if self.gec_hakki == 0:
                self.btn_gec.disabled = True

    def harf_al(self, instance):
        if not self.oyun_aktif or self.benjamin_aktif or self.animasyon_aktif:
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
        if not self.oyun_aktif or self.benjamin_aktif or self.animasyon_aktif:
            return
        self.benjamin_aktif = True
        self.benjamin_sure = 12
        self.ses_cal('benjamin.mp3')
        
        self.layout.remove_widget(self.alt_butonlar_kutusu)
        self.layout.add_widget(self.tahmin_kutusu)
        self.layout.add_widget(self.klavye_container)
        
        self.girilen_tahmin = ""
        self.tahmin_kutusu.text = "KLAVYEDEN YAZIN..."
        
        self.benjamin_event = Clock.schedule_interval(self.benjamin_timer_tick, 1)

    def benjamin_timer_tick(self, dt):
        self.benjamin_sure -= 1
        self.bilgi_label.text = f"SKOR: {self.puan}  |  BENJAMİN: {self.benjamin_sure}s"
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
        if self.gec_hakki > 0:
            self.btn_gec.disabled = False
        self.benjamin_aktif = False

    def cevap_kontrol(self, instance):
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
            self.show_feedback(False)
            self.kilitleri_ac()
            self.sonraki_soru()

    def ucan_efekt(self, metin, renk):
        self.efekt_label.text = metin
        self.efekt_label.color = renk
        self.efekt_label.opacity = 1
        Animation(pos_hint={'center_y': 0.72}, opacity=0, duration=1.2).start(self.efekt_label)

    def harfleri_sirayla_ac(self):
        self.animasyon_aktif = True
        cevap = self.mevcut_soru["cevap"]
        harf_indeksleri = [i for i, h in enumerate(cevap) if h not in (" ", ".", ",", "-")]
        for i, idx in enumerate(harf_indeksleri):
            Clock.schedule_once(lambda dt, index=idx: self._tek_harf_ac(index), i * 0.08)
        Clock.schedule_once(self.animasyon_bitir, len(harf_indeksleri) * 0.08 + 1)

    def animasyon_bitir(self, dt):
        self.animasyon_aktif = False
        self.kilitleri_ac()
        self.sonraki_soru()

    def _tek_harf_ac(self, index):
        if index not in self.acilan_harfler:
            self.acilan_harfler.append(index)
            self.kelime_guncelle()

    def timer_guncelle(self, dt):
        if self.sure > 0 and self.oyun_aktif and not self.benjamin_aktif:
            self.sure -= 1
            self.bilgi_label.text = f"SKOR: {self.puan}  |  SÜRE: {self.sure//60:02d}:{self.sure%60:02d}"
        elif self.sure <= 0 and self.oyun_aktif:
            self.oyun_bitti("SÜRE DOLDU!")

    def oyunu_sifirla(self):
        self.puan, self.sure, self.soru_sirasi, self.oyun_aktif = 0, 120, 0, True
        self.gec_hakki = 3
        self.yanlis_cevaplananlar.clear()
        self.btn_gec.metin_guncelle(f"GEÇ ({self.gec_hakki})")
        
        # HER YENİ OYUNDA 512 SORULUK HAVUZU TEKRAR YÜKLE VE KARIŞTIR
        self.soru_listesi = self.sorulari_yukle()
        
        self.kilitleri_ac()
        self.soru_yukle()

    def soru_yukle(self):
        if self.soru_sirasi < len(self.soru_listesi):
            self.mevcut_soru = self.soru_listesi[self.soru_sirasi]
            self.acilan_harfler = []
            self.soru_label.text = self.mevcut_soru["soru"]
            self.kelime_guncelle()
        else:
            self.oyun_bitti("TEBRİKLER!")

    def sonraki_soru(self):
        self.soru_sirasi += 1
        self.soru_yukle()

    def show_feedback(self, success):
        hedef_gorsel = 'dogru.png' if success else 'yanlis.png'
        if os.path.exists(hedef_gorsel):
            self.feedback_img.source = hedef_gorsel
            self.feedback_img.opacity = 1
            Clock.schedule_once(lambda dt: setattr(self.feedback_img, 'opacity', 0), 0.8)

    def oyun_bitti(self, mesaj):
        self.oyun_aktif = False
        
        if hasattr(self, 'mevcut_soru') and self.mevcut_soru:
            zaten_var = any(item["soru"] == self.mevcut_soru["soru"] for item in self.yanlis_cevaplananlar)
            if not zaten_var:
                self.yanlis_cevaplananlar.append({
                    "soru": self.mevcut_soru["soru"],
                    "cevap": self.mevcut_soru["cevap"],
                    "durum": "SÜRE YETMEDİ"
                })

        ana_kutu = BoxLayout(orientation='vertical', padding=20, spacing=15)
        
        lbl_skor = Label(
            text=f"{mesaj}\nTOPLAM SKORUNUZ: {self.puan}", 
            font_size='22sp', 
            bold=True, 
            color=(1, 0.85, 0.2, 1),
            halign='center'
        )
        ana_kutu.add_widget(lbl_skor)

        if self.yanlis_cevaplananlar:
            btn_cevaplar = Button(
                text=f"DOĞRU CEVAPLARI GÖR ({len(self.yanlis_cevaplananlar)} Soru) 🎁",
                size_hint=(1, None),
                height=52,
                background_color=(0.18, 0.5, 0.8, 1),
                bold=True,
                font_size='15sp',
                background_normal=''
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
                height=30
            )
            ana_kutu.add_widget(lbl_kusursuz)

        btn_yeniden = Button(
            text="YENİDEN OYNA", 
            size_hint=(1, None), 
            height=50, 
            background_color=(0, 0.75, 0.35, 1), 
            bold=True,
            font_size='16sp',
            background_normal=''
        )
        btn_yeniden.bind(on_release=lambda x: [self.oyunu_sifirla(), popup_bitti.dismiss()])
        ana_kutu.add_widget(btn_yeniden)

        popup_bitti = Popup(
            title='Oyun Bitti', 
            content=ana_kutu, 
            size_hint=(0.88, 0.46), 
            auto_dismiss=False
        )
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
        ana_kutu = BoxLayout(orientation='vertical', padding=15, spacing=10)

        scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False)
        liste_kutu = BoxLayout(orientation='vertical', spacing=8, size_hint_y=None)
        liste_kutu.bind(minimum_height=liste_kutu.setter('height'))

        for idx, item in enumerate(self.yanlis_cevaplananlar, start=1):
            soru_karti = BoxLayout(orientation='vertical', spacing=3, size_hint_y=None, height=75)
            with soru_karti.canvas.before:
                Color(0.12, 0.14, 0.18, 0.95)
                RoundedRectangle(pos=soru_karti.pos, size=soru_karti.size, radius=[8])
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
                text=f"Doğru Cevap: {item['cevap']} ({item['durum']})",
                font_size='14sp',
                bold=True,
                halign='left',
                valign='middle',
                color=(0.15, 0.85, 0.45, 1)
            )
            lbl_c.bind(size=lbl_c.setter('text_size'))
            soru_karti.add_widget(lbl_c)

            liste_kutu.add_widget(soru_karti)

        scroll.add_widget(liste_kutu)
        ana_kutu.add_widget(scroll)

        btn_kapat = Button(
            text="YENİDEN OYNA", 
            size_hint=(1, None), 
            height=46, 
            background_color=(0, 0.75, 0.35, 1), 
            bold=True,
            font_size='16sp',
            background_normal=''
        )
        btn_kapat.bind(on_release=lambda x: [self.oyunu_sifirla(), popup_detay.dismiss()])
        ana_kutu.add_widget(btn_kapat)

        popup_detay = Popup(
            title='Yanıtlanamayan Soruların Doğruları', 
            content=ana_kutu, 
            size_hint=(0.92, 0.80), 
            auto_dismiss=False
        )
        popup_detay.open()

    def _kart_ciz(self, inst):
        inst.canvas.before.clear()
        with inst.canvas.before:
            Color(0.12, 0.14, 0.18, 0.95)
            RoundedRectangle(pos=inst.pos, size=inst.size, radius=[8])
            Color(0.3, 0.35, 0.45, 0.5)
            Line(rounded_rectangle=(inst.x, inst.y, inst.width, inst.height, 8), width=1)

    def sorulari_yukle(self):
        liste = []
        if os.path.exists("sorular.txt"):
            with open("sorular.txt", "r", encoding="utf-8") as f:
                for s in f:
                    if "," in s:
                        q, a = s.strip().split(",", 1)
                        liste.append({"soru": q, "cevap": a.strip()})
        random.shuffle(liste)
        return liste

    def skor_tablosu_popup(self):
        l = BoxLayout(orientation='vertical', padding=20, spacing=10)
        l.add_widget(Label(text="Kayıtlı Skorlar:", font_size='18sp', bold=True))
        if os.path.exists("skorlar.txt"):
            with open("skorlar.txt", "r", encoding="utf-8") as f:
                icerik = f.read()
                l.add_widget(Label(text=icerik if icerik else "Henüz skor yok."))
        else:
            l.add_widget(Label(text="Henüz skor kaydı bulunamadı."))
        b = Button(text="KAPAT", size_hint=(1, 0.3), background_color=(0.2, 0.5, 0.8, 1))
        p = Popup(title='Skorlar', content=l, size_hint=(0.85, 0.5))
        b.bind(on_release=p.dismiss)
        l.add_widget(b)
        p.open()


class KelimeApp(App):
    def build(self):
        self.ads = None
        if platform == 'android' and KivMob:
            APP_ID = "ca-app-pub-4733411214953557~3933038318"
            INTERSTITIAL_ID = "ca-app-pub-4733411214953557/4410541306"

            try:
                self.ads = KivMob(APP_ID)
                self.ads.new_interstitial(INTERSTITIAL_ID)
                self.ads.request_interstitial()
            except Exception:
                pass

        sm = ScreenManager(transition=FadeTransition(duration=0.3))
        sm.add_widget(GirisEkrani(name='giris'))
        sm.add_widget(OyunEkrani(name='oyun'))
        return sm

    def on_pause(self):
        oyun_ekrani = self.root.get_screen('oyun')
        if oyun_ekrani and oyun_ekrani.bg_music:
            if oyun_ekrani.bg_music.state == 'play':
                oyun_ekrani.bg_music.stop()
        return True

    def on_resume(self):
        oyun_ekrani = self.root.get_screen('oyun')
        if oyun_ekrani and oyun_ekrani.bg_music and oyun_ekrani.ses_durumu:
            oyun_ekrani.bg_music.play()


if __name__ == '__main__':
    KelimeApp().run()