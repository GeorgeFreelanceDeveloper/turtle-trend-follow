# region imports
from AlgorithmImports import *
import datetime


# endregion

class TurtleV2(QCAlgorithm):

    INDEXES = {
        "SP500": {
            "stocks": ["NVDA", "MSFT", "AAPL", "AMZN", "META", "AVGO", "GOOGL", "BRK.B", "TSLA", "GOOG"],
            "benchmark_symbol": "SPY"
            # https://finance.yahoo.com/quote/SPY/holdings/
        },
        "NASDAQ100": {
            "stocks": ["NVDA", "MSFT", "AAPL", "AMZN", "AVGO", "META", "NFLX", "TSLA", "COST", "GOOGL"],
            "benchmark_symbol": "QQQ"
            # https://finance.yahoo.com/quote/QQQ/holdings/
        },
        "SP500 MOMENTUM": {
            "stocks": ["NVDA", "META", "AMZN", "AVGO", "JPM", "TSLA", "WMT", "NFLX", "PLTR", "COST"],
            "benchmark_symbol": "SPMO"
            # https://finance.yahoo.com/quote/SPMO/holdings/
        },
        "SP MEDIUM CAP MOMENTUM": {
            "stocks": ["IBKR", "EME", "SFM", "FIX", "GWRE", "USFD", "CRS", "EQH", "CW", "CASY"],
            "benchmark_symbol": "XMMO"
            # https://finance.yahoo.com/quote/XMMO/holdings/
        },
        "SP SMALL CAP MOMENTUM": {
            "stocks": ["EAT", "CORT", "COOP", "AWI", "IDCC", "SKYW", "JXN", "CALM", "DY", "SMTC"],
            "benchmark_symbol": "XSMO"
            # https://finance.yahoo.com/quote/XSMO/holdings/
        },
        "IPOX 100 US": {
            "stocks": ["GEV", "PLTR", "APP", "CEG", "RBLX", "DASH", "IBM", "HOOD", "TT", "IOT"],
            "benchmark_symbol": "FPX"
            # https://finance.yahoo.com/quote/FPX/
        }
    }

    BREAK_OUTS = {
        "YEARLY": {"entry": 250, "exit": 125},
        "SEMI-YEARLY": {"entry": 125, "exit": 62},
        "QUARTERLY": {"entry": 60, "exit": 30},
        "MONTHLY": {"entry": 20, "exit": 10},
        "WEEKLY": {"entry": 5, "exit": 3}
    }

    def initialize(self):

        # ********************************
        # User defined inputs
        # ********************************

        # Basic settings
        index = self.get_parameter("index", "SP500 MOMENTUM")
        breakout = self.get_parameter("breakout", "YEARLY")
        self.leverage = self.get_parameter("leverage", 0)

        # Filter settings
        self.enable_filter = True if (self.get_parameter("enable_filter", "True") == "True") else False

        # ********************************
        # Algorithm settings
        # ********************************

        # Basic
        self.set_start_date(datetime.date.today().year - 5, 1, 1)
        # self.set_end_date(2025,1,1)
        self.set_cash(10000)
        self.enable_automatic_indicator_warm_up = True

        self.benchmark_symbol = self.INDEXES[index]["benchmark_symbol"]
        self.symbols = self.INDEXES[index]["stocks"]
        self.markets = {symbol: self.add_equity(symbol, Resolution.DAILY, leverage=10) for symbol in self.symbols}
        self.add_equity(self.benchmark_symbol, Resolution.DAILY)

        # Init indicators
        self.dchs = {symbol: self.dch(symbol, self.BREAK_OUTS[breakout]["entry"], self.BREAK_OUTS[breakout]["exit"]) for
                     symbol in self.symbols}
        self.benchmark_sma200 = self.sma(self.benchmark_symbol, 200)

    def on_data(self, data: Slice):
        for symbol in self.symbols:
            dch = self.dchs[symbol]
            self.strategy(data, symbol, dch)

    def strategy(self, data, symbol, dch):
        # **********************************
        # Perform calculations and analysis
        # **********************************

        # Basic
        if symbol not in data.Bars or self.benchmark_symbol not in data.Bars:
            return

        bar = data.Bars[symbol]
        bar_benchmark = data.Bars[self.benchmark_symbol]

        # Filter
        filter = bar_benchmark.close > self.benchmark_sma200[1].value if self.enable_filter else True

        buy_condition = bar.close > dch.upper_band[1].value and filter and not self.portfolio[symbol].is_long
        sell_condition = bar.close < dch.lower_band[1].value if filter else True

        # ********************************
        # Manage trade
        # ********************************
        if buy_condition:
            self.set_holdings(symbol, (1 / len(self.symbols)) + (1 / len(self.symbols) * self.leverage))

        if sell_condition:
            self.liquidate(symbol)