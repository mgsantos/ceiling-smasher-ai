
# The Macro Universe
# Curated list of liquid ETFs representing global flows

COUNTRIES = [
    "EWZ",  # Brazil
    "FXI",  # China Large-Cap
    "KWEB", # China Internet
    "INDA", # India
    "EWW",  # Mexico
    "ARGT", # Argentina (High Vol)
    "EWG",  # Germany
    "EWJ",  # Japan
    "EWY",  # South Korea
    "TUR",  # Turkey (High Vol)
    "RSX",  # Russia (Likely frozen, but good to have in list structure)
    "EEM",  # Emerging Markets
    "VGK",  # Europe
    "ACWI", # World
]

COMMODITIES = [
    "GLD",  # Gold
    "GDX",  # Gold Miners
    "SLV",  # Silver
    "SILJ", # Junior Silver Miners
    "UNG",  # Natural Gas (The Widowmaker)
    "USO",  # Oil
    "XOP",  # Oil & Gas Exploration
    "URA",  # Uranium
    "CCJ",  # Cameco (Proxy)
    "COPX", # Copper Miners
    "LIT",  # Lithium
    "PALL", # Palladium
    "CORN", # Corn
    "DBA",  # Agriculture
]

SECTORS = [
    "XLF",  # Financials
    "XLE",  # Energy
    "XLK",  # Tech
    "XLV",  # Healthcare
    "XBI",  # Biotech (High Beta)
    "SMH",  # Semiconductors
    "XHB",  # Homebuilders
    "JETS", # Airlines
    "IWM",  # Russell 2000 (Small Caps)
    "TAN",  # Solar
    "ICLN", # Clean Energy
    "ARKK", # Innovation / Spec Growt
    "IPO",  # New Listings
    "BITO", # Bitcoin Strategy
]

BONDS_YIELDS = [
    "TLT",  # 20+ Year Treasury
    "TBT",  # Short 20+ Year (Yields Up)
    "HYG",  # High Yield Bonds (Risk On/Off)
    "LQD",  # Corporate Bonds
]

# Combined List
ALL_ETFS = list(set(COUNTRIES + COMMODITIES + SECTORS + BONDS_YIELDS))
