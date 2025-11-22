import requests
from kivy.app import App
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.core.window import Window

# ---- LIGHT THEME UI ----
Window.clearcolor = (1, 1, 1, 1)
PRIMARY_BLUE = (0.1, 0.45, 0.85, 1)
DARK_TEXT = (0, 0, 0, 1)
GREEN = (0, 0.65, 0.20, 1)
RED = (0.75, 0.1, 0.1, 1)

# ------------ LIVE PRICE FROM NSE INDIA ---------------
def get_nse_price(symbol):
    url = f"https://www.nseindia.com/api/quote-equity?symbol={symbol.upper()}"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://www.nseindia.com/"
    }
    try:
        resp = requests.get(url, headers=headers, timeout=5)
        data = resp.json()
        return data["priceInfo"]["lastPrice"]
    except:
        return None


# -------- Stock row UI --------
class StockRow(BoxLayout):
    def __init__(self, symbol, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "horizontal"
        self.size_hint_y = None
        self.height = 75
        self.padding = [15,15,15,15]
        self.spacing = 15

        self.symbol = symbol.upper()
        self.last_price = None

        self.lbl_symbol = Label(text=self.symbol, size_hint_x=0.30,
                                font_size=39, color=DARK_TEXT)

        self.lbl_price = Label(text="--", size_hint_x=0.4,
                               font_size=39, bold=True, color=DARK_TEXT)

        self.lbl_status = Label(text="Loading...", size_hint_x=0.30,
                                font_size=39, color=DARK_TEXT)

        self.add_widget(self.lbl_symbol)
        self.add_widget(self.lbl_price)
        self.add_widget(self.lbl_status)

    def update_price(self):
        price = get_nse_price(self.symbol)
        if price is None:
            self.lbl_price.text = "--"
            self.lbl_status.text = "No Data"
            self.lbl_price.color = DARK_TEXT
            return

        if self.last_price is not None:
            if price > self.last_price:
                self.lbl_price.color = GREEN
            elif price < self.last_price:
                self.lbl_price.color = RED
            else:
                self.lbl_price.color = DARK_TEXT

        self.last_price = price
        self.lbl_price.text = f"₹ {price:.2f}"
        self.lbl_status.text = "Updated"


# -------- Main App --------
class NSELiveApp(App):
    def build(self):
        self.title = "📊 NSE Live Price Tracker"

        root = BoxLayout(orientation="vertical", padding=15, spacing=6)

        # Input Bar
        top = BoxLayout(size_hint_y=None, height=75, spacing=5)
        self.entry = TextInput(hint_text="Enter symbol (TCS, INFY, HDFCBANK)",
                               multiline=False, font_size=38,
                               foreground_color=DARK_TEXT,
                               background_color=(0.97, 0.97, 0.97, 1),
                               padding=[10,10,10,10],
                               cursor_color=(0,0,0,1))
        btn_add = Button(text="Add", size_hint_x=0.48,
                         font_size=35, bold=True,
                         background_color=PRIMARY_BLUE,
                         color=(1,1,1,1),
                         on_press=self.add_symbol)
        top.add_widget(self.entry)
        top.add_widget(btn_add)
        root.add_widget(top)

        # Status
        self.status = Label(text="Enter a symbol and press Add",
                            size_hint_y=None, height=30,
                            font_size=25, color=DARK_TEXT)
        root.add_widget(self.status)

        # Scroll Watchlist
        self.scroll = ScrollView()
        self.grid = GridLayout(cols=1, spacing=4, size_hint_y=None, padding=[0,5,0,5])
        self.grid.bind(minimum_height=self.grid.setter("height"))
        self.scroll.add_widget(self.grid)
        root.add_widget(self.scroll)

        # Bottom buttons
        bottom = BoxLayout(size_hint_y=None, height=48, spacing=5)
        bottom.add_widget(Button(text="Refresh",
                                 font_size=33, bold=True,
                                 background_color=PRIMARY_BLUE,
                                 color=(1,1,1,1),
                                 on_press=self.manual_refresh))
        self.refresh_label = Label(text="Auto refresh every mili sec",
                                   font_size=33, color=DARK_TEXT)
        bottom.add_widget(self.refresh_label)
        root.add_widget(bottom)

        self.watchlist = {}
        Clock.schedule_interval(self.auto_update, .1)
        return root

    def add_symbol(self, instance):
        symbol = self.entry.text.strip().upper()
        if not symbol:
            self.status.text = "⚠ Enter a symbol!"
            return
        if symbol in self.watchlist:
            self.status.text = f"ℹ {symbol} already exists"
            return
        row = StockRow(symbol)
        self.watchlist[symbol] = row
        self.grid.add_widget(row)
        row.update_price()
        self.status.text = f"✔ {symbol} added"
        self.entry.text = ""

    def auto_update(self, dt):
        for row in self.watchlist.values():
            row.update_price()

    def manual_refresh(self, instance):
        for row in self.watchlist.values():
            row.update_price()
        self.status.text = "🔄 Refreshed"


if __name__ == "__main__":
    NSELiveApp().run()