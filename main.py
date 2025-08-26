import requests
import os
import smtplib
import streamlit as st
from email.mime.text import MIMEText

st.set_page_config(layout="wide")
BASE_URL = f"{'https://api.coingecko.com/api/v3/'}"
API_KEY = st.secrets["API_KEY"]

headers = {
    "accept": "application/json",
    "x-cg-demo-api-key": API_KEY
}

# 1. Total marketcap alcoins (except BTC & ETH)
def get_total3_marketcap():
    url = f"{BASE_URL}/global"
    r = requests.get(url, headers=headers)
    data = r.json()
    total_marketcap = data["data"]["total_market_cap"]["usd"]
    btc_marketcap = data["data"]["market_cap_percentage"]["btc"] * total_marketcap / 100
    eth_marketcap = data["data"]["market_cap_percentage"]["eth"] * total_marketcap / 100
    total3 = total_marketcap - btc_marketcap - eth_marketcap
    return {"total_marketcap_usd": total_marketcap, "total3_usd": total3}

# 2. Altcoins volume
def get_total3_volume():
    url = f"{BASE_URL}/global"
    r = requests.get(url, headers=headers)
    data = r.json()
    total_volume = data["data"]["total_volume"]["usd"]
    return {"total_volume_usd": total_volume}

# 3. Trends
def get_trending_coins():
    url = f"{BASE_URL}/search/trending"
    r = requests.get(url, headers=headers)
    data = r.json()
    trending = [coin["item"]["name"] for coin in data["coins"]]
    return trending

# 4. Fear & Greed Index
def get_fear_greed():
    url = "https://api.alternative.me/fng/"
    r = requests.get(url, headers=headers)
    data = r.json()
    return {"value": data["data"][0]["value"], "classification": data["data"][0]["value_classification"]}

# 5. Rotation sectorielle
def get_top_sectors():
    url = f"{BASE_URL}/coins/categories"
    r = requests.get(url, headers=headers)
    data = r.json()
    return [{"name": cat["name"], "market_cap": cat["market_cap"]} for cat in data[:5]]

# 6. BTC.D
def get_btc_dominance():
    url = f"{BASE_URL}/global"
    data = requests.get(url).json()
    return data["data"]["market_cap_percentage"]["btc"]

# 7. ETH/BTC
def get_eth_btc_ratio():
    url = f"{BASE_URL}/simple/price?ids=bitcoin,ethereum&vs_currencies=usd"
    data = requests.get(url).json()
    return data["ethereum"]["usd"] / data["bitcoin"]["usd"]

btc_dom = get_btc_dominance()
eth_btc = get_eth_btc_ratio()
total_marketcap = get_total3_marketcap()
total3_volume = get_total3_volume()
trends = get_trending_coins()
f_g = get_fear_greed()
sector_rotate = get_top_sectors()

kpi_essential = 0
kpi_count = 0

st.title('KPIs state')
st.divider()

left_col, right_col = st.columns([1, 1])
with left_col:

    with st.container():
        if (btc_dom < 48):
            st.header('1️⃣ Bitcoin dominance : ✅')
            st.subheader(f"Valeur: {btc_dom:.2f}%")
            kpi_essential += 1
        else:
            st.header('1️⃣ Bitcoin dominance : ❌')
            st.subheader(f"Valeur: {btc_dom:.2f}%")
        st.caption("Quand la dominance du BTC baisse après une phase haussière prolongée → signal que les capitaux se déplacent vers les alts. Seuils souvent observés : une cassure baissière de la dominance sous 50-48 % est un déclencheur fréquent.")
        st.divider()

        if (eth_btc > 0.06):
            st.header('2️⃣ ETH/BTC ratio : ✅')
            st.subheader(f"Valeur: {eth_btc:.4f}")
            kpi_essential += 1
        else:
            st.header('2️⃣ ETH/BTC ratio : ❌')
            st.subheader(f"Valeur: {eth_btc:.4f}")
        st.caption("Quand l'ETH surperforme le BTC (ETH/BTC > 0,06) → signal que les investisseurs se tournent vers les altcoins. Seuils souvent observés : un ratio ETH/BTC supérieur à 0,06 indique une tendance haussière pour les alts.")
    
    st.header("📈 Indicateurs Secondaires", divider="gray")

    if (int(f_g["value"]) > 60):
        st.header('Sentiment (Fear & Greed) : ✅')
        st.subheader(f"Valeur: {f_g['value']} ({f_g['classification']})")
        kpi_count += 1
    else:
        st.header('Sentiment (Fear & Greed) : ❌')
        st.subheader(f"Valeur: {f_g['value']} ({f_g['classification']})")
    st.caption("Quand l'indice de peur et de cupidité (Fear & Greed Index) est supérieur à 60 → signal que les investisseurs sont optimistes et se tournent vers les altcoins. Seuils souvent observés : un indice supérieur à 60 indique une tendance haussière pour les alts.")
    st.divider()

    if (total_marketcap["total3_usd"] > 150_000_000_000):
        st.header('TOTAL3 marketcap : ✅')
        st.subheader(f"Valeur: {total_marketcap['total3_usd'] / 1e9:.2f}B$")
        kpi_count += 1
    else:
        st.header('TOTAL3 marketcap : ❌')
        st.subheader(f"Valeur: {total_marketcap['total3_usd'] / 1e9:.2f}B$")
    st.caption("Quand la capitalisation totale des altcoins (hors BTC & ETH) dépasse 150 milliards de dollars → signal que les investisseurs se tournent vers les altcoins. Seuils souvent observés : une capitalisation totale des altcoins supérieure à 150 milliards de dollars indique une tendance haussière pour les alts.")
    st.divider()

    if (total3_volume["total_volume_usd"] > 30_000_000_000):
        st.header('TOTAL3 volume : ✅')
        st.subheader(f"Valeur: {total3_volume['total_volume_usd'] / 1e9:.2f}B$")
        kpi_count += 1
    else:
        st.header('TOTAL3 volume : ❌')
        st.subheader(f"Valeur: {total3_volume['total_volume_usd'] / 1e9:.2f}B$")
    st.caption("Quand le volume total des altcoins (hors BTC & ETH) dépasse 30 milliards de dollars → signal que les investisseurs se tournent vers les altcoins. Seuils souvent observés : un volume total des altcoins supérieur à 30 milliards de dollars indique une tendance haussière pour les alts.")
    st.divider()

    if (len(trends) >= 5):
        st.header('Nombre de coins en tendance : ✅')
        st.subheader(f"Valeurs: {', '.join(trends[:5])}")
        kpi_count += 1
    else:
        st.header('Nombre de coins en tendance : ❌')
        st.subheader(f"Valeurs: {', '.join(trends[:5])}")
    st.caption("Quand au moins 5 coins sont en tendance sur CoinGecko → signal que les investisseurs se tournent vers les altcoins. Seuils souvent observés : la présence d'au moins 5 coins en tendance indique une tendance haussière pour les alts.")
    st.divider()

    if (any(cat["market_cap"] > 10_000_000_000 for cat in sector_rotate)):
        st.header('Rotation sectorielle : ✅')
        st.subheader(f"Valeurs: {[cat['name'] for cat in sector_rotate[:3]]}")
        kpi_count += 1
    else:
        st.header('Rotation sectorielle : ❌')
        st.subheader(f"Valeurs: {[cat['name'] for cat in sector_rotate[:3]]}")
    st.caption("Quand au moins un secteur a une capitalisation de marché supérieure à 10 milliards de dollars → signal que les investisseurs se tournent vers les altcoins. Seuils souvent observés : la présence d'au moins un secteur avec une capitalisation de marché supérieure à 10 milliards de dollars indique une tendance haussière pour les alts.")
    st.divider()
with right_col:
    st.header(f"Etats des indicateurs : {kpi_count} / 7")
    st.subheader("Interprétation des résultats", divider="gray")
    if kpi_essential==2 & kpi_count >= 2:
        st.success("🏃‍➡️ Début d'altseason probable !")
    elif kpi_essential==2 & kpi_count >= 4:
        st.success("🚀 Altseason confirmée !")
    else:
        st.error("⛔️ Pas d'altseason pour le moment.")
    st.caption("Si 2 primaires + au moins 2 secondaires sont validés → début d’alt season probable.")
    st.caption("Si 2 primaires + 4 ou 5 secondaires sont validés → alt season confirmée.")
    st.caption("Si uniquement les secondaires sans les primaires → c’est plutôt un mini-alt rally local, pas une alt season complète.")
