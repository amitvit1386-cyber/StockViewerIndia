import json, os, requests
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle
from kivy.core.audio import SoundLoader
from kivy.utils import platform

# Android TTS & Vibration
try:
    from jnius import autoclass
except:
    autoclass = None

# Desktop TTS
try:
    import pyttsx3
except:
    pyttsx3 = None

# ===============================================
# GLOBAL SETTINGS
# ===============================================
FONT = 30
ROW_HEIGHT = FONT * 2.4
SAVE_FILE = "stocks.json"
HEADERS = {"User-Agent": "Mozilla/5.0"}

# ===============================================
# THEMES
# ===============================================
THEMES = {
    "light": {"bg": (1,1,1,1), "text": (0,0,0,1)},
    "dark":  {"bg": (0.05,0.05,0.05,1), "text": (1,1,1,1)}
}

current_theme = "light"
Window.clearcolor = THEMES[current_theme]["bg"]

# ===============================================
# LOAD + SAVE
# ===============================================
def load_watchlist():
    if os.path.exists(SAVE_FILE):
        data = json.load(open(SAVE_FILE))
        for s, d in data.items():
            if isinstance(d.get("alert"), dict):
                d["alert"] = None
        return data
    return {}

def save_watchlist(data):
    json.dump(data, open(SAVE_FILE, "w"))

# ===============================================
# APPLICATION
# ===============================================
class NSETracker(App):
    watchlist = {}
    auto_update = True
    alert_sound = None

    # 🎵🔔 SAFE MULTI-PLATFORM SOUND / VIBRATION
    def play_alert_sound(self):
        try:
            if not self.alert_sound:
                self.alert_sound = SoundLoader.load("alert.wav")
            if self.alert_sound:
                self.alert_sound.play()
        except:
            pass

        # Vibration Android
        try:
            if platform == "android" and autoclass:
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                activity = PythonActivity.mActivity
                Context = autoclass('android.content.Context')
                vibrator = activity.getSystemService(Context.VIBRATOR_SERVICE)
                vibrator.vibrate(700)
        except:
            pass

        try:
            print("\a")
        except:
            pass

    # 📣🎤 VOICE ALERT (ENGLISH-US)
    def speak_alert(self, sym, price):
        message = f"{sym} reached target price {price}"
        # Android TTS
        try:
            if platform == "android" and autoclass:
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                activity = PythonActivity.mActivity
                TextToSpeech = autoclass('android.speech.tts.TextToSpeech')
                Locale = autoclass('java.util.Locale')

                tts = TextToSpeech(activity, None)
                tts.setLanguage(Locale.US)
                tts.speak(message, TextToSpeech.QUEUE_FLUSH, None, None)
                return
        except:
            pass

        # Desktop TTS
        try:
            if pyttsx3:
                engine = pyttsx3.init()
                voices = engine.getProperty('voices')
                for v in voices:
                    if "en_US" in v.id or "us" in v.id.lower():
                        engine.setProperty('voice', v.id)
                        break
                engine.say(message)
                engine.runAndWait()
                return
        except:
            pass

        print(message)

    # ===============================================
    # UI BUILD
    # ===============================================
    def build(self):
        self.watchlist = load_watchlist()

        root = BoxLayout(orientation="vertical", padding=10, spacing=4)

        # -------- TOP INPUT --------
        top = BoxLayout(size_hint=(1, 0.09), spacing=4)
        self.ticker_in = TextInput(
            hint_text="Ticker (TCS/INFY)", font_size=FONT,
            multiline=False, background_color=[1,1,1,1],
            foreground_color=[0,0,0,1], size_hint=(0.55, .75)
        )
        add_btn = Button(text="ADD", font_size=FONT,
                         size_hint=(0.45, .75), background_color=[0.6, 0.3, 0, 1])
        add_btn.bind(on_press=lambda x: self.add_stock())
        top.add_widget(self.ticker_in); top.add_widget(add_btn)

        # -------- HEADER --------
        header = BoxLayout(size_hint=(1, 0.08), spacing=5)

        def colored_header(text, width):
            box = BoxLayout(size_hint=(width, 1))
            with box.canvas.before:
                Color(0.6, 0.8, 1, 1)
                box.bg = Rectangle(pos=box.pos, size=box.size)
            box.bind(pos=lambda inst, val: setattr(box.bg, "pos", val),
                     size=lambda inst, val: setattr(box.bg, "size", val))
            box.add_widget(Label(text=text, font_size=FONT, bold=True,
                                 color=[1,1,0,1]))
            return box

        header.add_widget(colored_header("STOCK", 0.33))
        header.add_widget(colored_header("PRICE", 0.27))
        header.add_widget(colored_header("ACTIONS", 0.4))

        # -------- LIST SCROLL --------
        self.stock_box = BoxLayout(orientation="vertical", spacing=6, size_hint_y=None)
        self.stock_box.bind(minimum_height=self.stock_box.setter("height"))
        scroll = ScrollView(size_hint=(1, 0.66))
        scroll.add_widget(self.stock_box)

        # -------- BOTTOM BAR --------
        bottom = BoxLayout(size_hint=(1, 0.09), spacing=5)
        refresh_btn = Button(text="REFRESH", font_size=FONT,
                             size_hint=(0.33,.8), background_color=[0,0.5,0.3,1])
        refresh_btn.bind(on_press=lambda x: self.refresh_prices())

        auto_btn = Button(text="AUTO ON", font_size=FONT,
                          size_hint=(0.33,.8), background_color=[0,0.6,0,1])
        auto_btn.bind(on_press=lambda x: self.toggle_auto())
        self.auto_btn = auto_btn

        theme_btn = Button(text="THEME", font_size=FONT,
                           size_hint=(0.34,.8), background_color=[0.4,0.4,1,1])
        theme_btn.bind(on_press=lambda x: self.toggle_theme())

        bottom.add_widget(refresh_btn); bottom.add_widget(auto_btn); bottom.add_widget(theme_btn)

        root.add_widget(top); root.add_widget(header); root.add_widget(scroll); root.add_widget(bottom)

        Clock.schedule_interval(lambda dt: self.auto_refresh(), 2)
        self.refresh_prices()
        return root

    # ===============================================
    # UI REFRESH + ROWS
    # ===============================================
    def text_color(self):
        return THEMES[current_theme]["text"]

    def reload_ui(self):
        self.stock_box.clear_widgets()

        for sym, data in self.watchlist.items():
            row = BoxLayout(size_hint_y=None, height=ROW_HEIGHT, spacing=5)

            # Stock + Bell
            bell = "🔔 " if data.get("alert") else ""
            stock_box = BoxLayout(size_hint=(0.33,1))
            stock_box.add_widget(Label(text=bell + sym, font_size=FONT,
                                       color=self.text_color()))
            row.add_widget(stock_box)

            # Price Color (Green / Red)
            price = data.get("price")
            prev = data.get("prev")
            pcolor = self.text_color()
            if isinstance(price, (int,float)) and isinstance(prev, (int,float)):
                if price > prev: pcolor = [0,1,0,1]
                elif price < prev: pcolor = [1,0,0,1]

            row.add_widget(Label(text=str(price if price is not None else "--"),
                                 font_size=FONT, color=pcolor, size_hint=(0.27,1)))

            # Buttons
            actions = BoxLayout(size_hint=(0.4,1), spacing=4)
            edit = Button(text="EDIT", font_size=FONT, background_color=[1,0.7,0,1])
            edit.bind(on_press=lambda x, s=sym: self.edit_stock(s))

            alert = Button(text="ALERT", font_size=FONT, background_color=[1,0,0.2,1])
            alert.bind(on_press=lambda x, s=sym: self.set_alert(s))

            delete = Button(text="DEL", font_size=FONT, background_color=[0.8,0,0,1])
            delete.bind(on_press=lambda x, s=sym: self.delete_stock(s))

            actions.add_widget(edit); actions.add_widget(alert); actions.add_widget(delete)
            row.add_widget(actions); self.stock_box.add_widget(row)

    # ===============================================
    # BUTTON ACTIONS
    # ===============================================
    def add_stock(self):
        sym = self.ticker_in.text.strip().upper()
        if not sym: return
        self.watchlist[sym] = {"price":None, "alert":None}
        save_watchlist(self.watchlist)
        self.ticker_in.text=""
        self.refresh_prices()

    def delete_stock(self, sym):
        self.watchlist.pop(sym, None)
        save_watchlist(self.watchlist)
        self.reload_ui()

    def edit_stock(self, sym):
        popup = Popup(title=f"Edit {sym}", size_hint=(0.7,0.4))
        box = BoxLayout(orientation="vertical", spacing=10, padding=10)
        inp = TextInput(text=sym, multiline=False, font_size=FONT)
        ok = Button(text="UPDATE", font_size=FONT, background_color=[0,0.5,1,1])
        ok.bind(on_press=lambda x: self.finish_edit(sym, inp.text, popup))
        box.add_widget(inp); box.add_widget(ok); popup.add_widget(box); popup.open()

    def finish_edit(self, old, new, popup):
        new = new.strip().upper()
        if not new: return
        self.watchlist[new] = self.watchlist.pop(old)
        save_watchlist(self.watchlist)
        popup.dismiss(); self.reload_ui()

    def set_alert(self, sym):
        popup = Popup(title=f"Set Alert {sym}", size_hint=(0.7,0.4))
        box = BoxLayout(orientation="vertical", spacing=10, padding=10)
        inp = TextInput(hint_text="Enter target price", multiline=False, font_size=FONT)
        ok = Button(text="SAVE", font_size=FONT, background_color=[1,0.4,0.1,1])
        ok.bind(on_press=lambda x: self.save_alert(sym, inp.text, popup))
        box.add_widget(inp); box.add_widget(ok); popup.add_widget(box); popup.open()

    def save_alert(self, sym, val, popup):
        try: self.watchlist[sym]["alert"] = float(val)
        except: self.watchlist[sym]["alert"] = None
        save_watchlist(self.watchlist)
        popup.dismiss()
        self.reload_ui()

    # ===============================================
    # ALERT CHECK (UPDATED WITH OK BUTTON)
    # ===============================================
    def check_alerts(self):
        for sym, d in self.watchlist.items():
            price, alert = d.get("price"), d.get("alert")
            if price and isinstance(alert,(int,float)) and price >= alert:

                self.play_alert_sound()
                self.speak_alert(sym, price)

                # UPDATED ALERT POPUP WITH OK BUTTON
                popup = Popup(title="🚨 ALERT HIT!", size_hint=(0.6,0.4))
                box = BoxLayout(orientation="vertical", spacing=10, padding=10)

                msg = Label(text=f"{sym} reached ₹{price}", font_size=FONT)
                ok_btn = Button(text="OK", font_size=FONT,
                                background_color=[0, 0.6, 0, 1])  # Green OK Button
                ok_btn.bind(on_press=lambda x: popup.dismiss())

                box.add_widget(msg)
                box.add_widget(ok_btn)
                popup.add_widget(box)
                popup.open()

                d["alert"] = None
                save_watchlist(self.watchlist)
                self.reload_ui()

    # ===============================================
    # REFRESH + AUTO
    # ===============================================
    def fetch_price(self, sym):
        try:
            return requests.get(
                f"https://www.nseindia.com/api/quote-equity?symbol={sym}",
                headers=HEADERS).json()["priceInfo"]["lastPrice"]
        except:
            return None

    def refresh_prices(self):
        for s in self.watchlist:
            old = self.watchlist[s].get("price")
            new = self.fetch_price(s)
            self.watchlist[s]["prev"] = old
            self.watchlist[s]["price"] = new
        save_watchlist(self.watchlist)
        self.check_alerts()
        self.reload_ui()

    def auto_refresh(self):
        if self.auto_update:
            self.refresh_prices()

    def toggle_auto(self):
        self.auto_update = not self.auto_update
        self.auto_btn.text = "AUTO ON" if self.auto_update else "AUTO OFF"

    def toggle_theme(self):
        global current_theme
        current_theme = "dark" if current_theme == "light" else "light"
        Window.clearcolor = THEMES[current_theme]["bg"]
        self.reload_ui()

# ===============================================
# RUN APP
# ===============================================
if __name__ == "__main__":
    NSETracker().run()