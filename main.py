import requests
import smtplib
from email.mime.text import MIMEText

BASE_URL = f"{'https://api.coingecko.com/api/v3/'}"


# 1. Total marketcap alcoins (except BTC & ETH)
def get_total3_marketcap():
    url = f"{BASE_URL}/global"
    r = requests.get(url)
    data = r.json()
    total_marketcap = data["data"]["total_market_cap"]["usd"]
    btc_marketcap = data["data"]["market_cap_percentage"]["btc"] * total_marketcap / 100
    eth_marketcap = data["data"]["market_cap_percentage"]["eth"] * total_marketcap / 100
    total3 = total_marketcap - btc_marketcap - eth_marketcap
    return {"total_marketcap_usd": total_marketcap, "total3_usd": total3}

# 2. Altcoins volume
def get_total3_volume():
    url = f"{BASE_URL}/global"
    r = requests.get(url)
    data = r.json()
    total_volume = data["data"]["total_volume"]["usd"]
    return {"total_volume_usd": total_volume}

# 3. Trends
def get_trending_coins():
    url = f"{BASE_URL}/search/trending"
    r = requests.get(url)
    data = r.json()
    trending = [coin["item"]["name"] for coin in data["coins"]]
    return trending

# 4. Fear & Greed Index
def get_fear_greed():
    url = "https://api.alternative.me/fng/"
    r = requests.get(url)
    data = r.json()
    return {"value": data["data"][0]["value"], "classification": data["data"][0]["value_classification"]}

# 5. Rotation sectorielle
def get_top_sectors():
    url = f"{BASE_URL}/coins/categories"
    r = requests.get(url)
    data = r.json()
    top_categories = sorted(data, key=lambda x: x["market_cap"], reverse=True)[:5]
    return [{"name": cat["name"], "market_cap": cat["market_cap"]} for cat in top_categories]

# BTC.D
def get_btc_dominance():
    url = f"{BASE_URL}/global"
    data = requests.get(url).json()
    return data["data"]["market_cap_percentage"]["btc"]

# ETH/BTC
def get_eth_btc_ratio():
    url = f"{BASE_URL}/simple/price?ids=bitcoin,ethereum&vs_currencies=usd"
    data = requests.get(url).json()
    return data["ethereum"]["usd"] / data["bitcoin"]["usd"]

# Mail alerting
def send_alert(message):
    msg = MIMEText(message)
    msg["Subject"] = "🚨 Signal Altseason détecté"
    msg["From"] = "mehdbest.king@gmail.com"
    msg["To"] = "mbouazzapro@gmail.com"

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login("mehdbest.king@gmail.com", "ton_mot_de_passe_app")
        server.send_message(msg)

# Check des conditions
btc_dom = get_btc_dominance()
eth_btc = get_eth_btc_ratio()
total_marketcap = get_total3_marketcap()
total3_volume = get_total3_volume()
trends = get_trending_coins()
f_g = get_fear_greed()
sector_rotate = get_top_sectors()

if (
    btc_dom < 48                                                            # 1. BTC dominance en baisse
    and eth_btc > 0.06                                                      # 2. ETH surperforme BTC
    and total_marketcap["total3_usd"] > 150_000_000_000                     # 3. Market cap altcoins (TOTAL3) > 150B
    and total3_volume["total_volume_usd"] > 30_000_000_000                  # 4. Volumes importants > 30B
    and len(trends) >= 5                                                    # 5. Narratifs actifs (≥5 coins en tendance)
    and int(f_g["value"]) > 60                                              # 6. Fear & Greed > 60 = Greed/FOMO
    and any(cat["market_cap"] > 10_000_000_000 for cat in sector_rotate)    # 7. Rotation sectorielle : gros secteurs > 10B
):
    send_alert(
        f"""🚨 Alerte potentielle Alt Season 🚨
        BTC Dominance: {btc_dom:.2f}%
        ETH/BTC: {eth_btc:.4f}
        TOTAL3: {total_marketcap['total3_usd'] / 1e9:.2f}B$
        Volume: {total3_volume['total_volume_usd'] / 1e9:.2f}B$
        Fear & Greed: {f_g['value']} ({f_g['classification']})
        Top sectors: {[cat['name'] for cat in sector_rotate[:3]]}
        Coins tendances: {', '.join(trends[:5])}
        ✅ Possible début d'Alt Season !
        """
    )
else:
    print("Rien à signaler 🚀")
