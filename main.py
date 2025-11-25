import os
import streamlit as st
import requests
import pandas as pd
import yfinance as yf
import numpy as np

# --- CONFIGURATION ---
st.set_page_config(layout="wide", page_title="Liquidity Tracker")
API_KEY = os.getenv("API_KEY") # Ton API Key CoinGecko
HEADERS = {"accept": "application/json", "x-cg-demo-api-key": API_KEY}

# --- FONCTIONS DE RECUPERATION DE DONNEES (CACHÉES POUR LA PERF) ---

@st.cache_data(ttl=3600) # Cache les données 1h pour éviter de spammer les API
def get_macro_data():
    """Récupère les données TradFi via Yahoo Finance"""
    # Tickers: ^TNX (10Y Yield), DX-Y.NYB (DXY), SPY (S&P500 ETF), TLT (Bonds ETF), XLK (Tech ETF)
    tickers = ["^TNX", "DX-Y.NYB", "SPY", "TLT", "XLK"]
    data = yf.download(tickers, period="6mo", interval="1d", progress=False)['Close']
    return data

@st.cache_data(ttl=300)
def get_btc_technical_data():
    """Récupère l'historique BTC pour calculer OBV, MFI et VWAP"""
    # On prend plus de data pour que les indicateurs se lissent
    btc = yf.download("BTC-USD", period="3mo", interval="1d", progress=False)
    return btc

def get_coingecko_global():
    url = "https://api.coingecko.com/api/v3/global"
    try:
        return requests.get(url, headers=HEADERS).json()["data"]
    except:
        return None

def get_stablecoins_history():
    """
    Récupère l'historique de market cap USDT + USDC sur 3 mois.
    Retourne un DataFrame Pandas avec la somme des deux.
    """
    ids = ["tether", "usd-coin"]
    df_total = pd.DataFrame()

    for coin_id in ids:
        # Endpoint pour l'historique (days=180, interval=daily pour alléger)
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
        params = {
            "vs_currency": "usd",
            "days": "180",
            "interval": "daily"
        }
        try:
            r = requests.get(url, headers=HEADERS, params=params)
            data = r.json()
            
            # On extrait les données de market_cap [[timestamp, value], ...]
            mcap_data = data.get('market_caps', [])
            
            # Création d'un DF temporaire pour ce coin
            df_temp = pd.DataFrame(mcap_data, columns=['timestamp', 'mcap'])
            df_temp['date'] = pd.to_datetime(df_temp['timestamp'], unit='ms')
            df_temp.set_index('date', inplace=True)
            
            # On renomme la colonne pour éviter les conflits lors du merge
            df_temp.rename(columns={'mcap': coin_id}, inplace=True)
            
            # Fusion avec le DF principal
            if df_total.empty:
                df_total = df_temp[[coin_id]]
            else:
                # Outer join pour aligner les dates si elles diffèrent légèrement
                df_total = df_total.join(df_temp[[coin_id]], how='outer')
                
        except Exception as e:
            st.error(f"Erreur récupération {coin_id}: {e}")
            return None

    # On remplit les trous éventuels (interpolation) et on fait la somme
    df_total = df_total.interpolate(method='time')
    df_total['total_liquidity'] = df_total['tether'] + df_total['usd-coin']
    
    return df_total['total_liquidity']
# --- CALCUL DES INDICATEURS ---

def calculate_obv(df):
    """On-Balance Volume"""
    df['OBV'] = (np.sign(df['Close'].diff()) * df['Volume']).fillna(0).cumsum()
    return df['OBV']

def calculate_mfi(df, period=14):
    """Money Flow Index"""
    typical_price = (df['High'] + df['Low'] + df['Close']) / 3
    money_flow = typical_price * df['Volume']
    
    positive_flow = money_flow.where(typical_price > typical_price.shift(1), 0)
    negative_flow = money_flow.where(typical_price < typical_price.shift(1), 0)
    
    mf_ratio = positive_flow.rolling(period).sum() / negative_flow.rolling(period).sum()
    mfi = 100 - (100 / (1 + mf_ratio))
    return mfi

def calculate_vwap(df):
    """VWAP simple sur la période téléchargée"""
    v = df['Volume'].values
    tp = (df['High'] + df['Low'] + df['Close']) / 3
    return (tp * v).cumsum() / v.cumsum()

# --- MAIN APP ---

st.title('🌊 Liquidity & Market Flow Tracker')
st.markdown("Analyse des flux macro-économiques et crypto pour déterminer la direction de la liquidité.")
st.divider()

# 1. Chargement des données
with st.spinner('Récupération des données Macro & Crypto...'):
    macro_df = get_macro_data()
    btc_df = get_btc_technical_data()
    cg_global = get_coingecko_global()
    stable_mcap = get_stablecoins_history()

# 2. Traitement MACRO
# Calcul des variations pour la tendance
tnx_change5d = macro_df['^TNX'].iloc[-1] - macro_df['^TNX'].iloc[-5]
tnx_change15d = macro_df['^TNX'].iloc[-1] - macro_df['^TNX'].iloc[-15]
tnx_change30d = macro_df['^TNX'].iloc[-1] - macro_df['^TNX'].iloc[-30]
dxy_change5d = macro_df['DX-Y.NYB'].iloc[-1] - macro_df['DX-Y.NYB'].iloc[-5]
dxy_change15d = macro_df['DX-Y.NYB'].iloc[-1] - macro_df['DX-Y.NYB'].iloc[-15]
dxy_change30d = macro_df['DX-Y.NYB'].iloc[-1] - macro_df['DX-Y.NYB'].iloc[-30]

# SPY/TLT Ratio
spy_tlt_ratio = macro_df['SPY'] / macro_df['TLT']
ratio_trend5d = spy_tlt_ratio.iloc[-1] - spy_tlt_ratio.iloc[-5]
ratio_trend15d = spy_tlt_ratio.iloc[-5] - spy_tlt_ratio.iloc[-15]
ratio_trend30d = spy_tlt_ratio.iloc[-15] - spy_tlt_ratio.iloc[-30]

# Rotation XLK/SPY
xlk_spy_ratio = macro_df['XLK'] / macro_df['SPY']
rotation_trend5d = xlk_spy_ratio.iloc[-1] - xlk_spy_ratio.iloc[-5]
rotation_trend15d = xlk_spy_ratio.iloc[-5] - xlk_spy_ratio.iloc[-15]
rotation_trend30d = xlk_spy_ratio.iloc[-15] - xlk_spy_ratio.iloc[-30]

# 3. Traitement MICRO (BTC)
# OBV
obv = calculate_obv(btc_df)
obv_trend5d = "Hausse" if obv.iloc[-1] > obv.iloc[-5] else "Baisse"
obv_trend15d = "Hausse" if obv.iloc[-1] > obv.iloc[-5] else "Baisse"
obv_trend30d = "Hausse" if obv.iloc[-1] > obv.iloc[-5] else "Baisse"

# MFI
mfi = calculate_mfi(btc_df)
current_mfi = mfi.iloc[-1]

# VWAP (Comparaison prix actuel vs VWAP du mois)
# On recalcul un VWAP local sur les 30 derniers jours
btc_30d = btc_df.tail(30).copy()
btc_30d['VWAP'] = (btc_30d['Volume'] * (btc_30d['High']+btc_30d['Low']+btc_30d['Close'])/3).cumsum() / btc_30d['Volume'].cumsum()
price_vs_vwap = btc_df['Close'].iloc[-1] > btc_30d['VWAP'].iloc[-1]

# --- AFFICHAGE ---

col1, col2 = st.columns(2)

with col1:
    st.header("🌍 Macro Economics")
    
    # 1. Bonds vs Actions (Risk On/Off)
    st.subheader("1. Taux Obligataires (US 10Y)", help="Les taux baissent : Bon pour la liquidité car le rendement obligataire diminue obligeant la liquidité a cherché du rendement dans les actifs à risque. Les taux montent : Pression sur les actifs à risque car le rendement obligataire attire la liquidité.")
    col_main, col_var1, col_var2 = st.columns([2, 1, 1])
    with col_main:
        st.metric(
            label="Rendement 10 ans (delta 5j)", 
            value=f"{macro_df['^TNX'].iloc[-1]:.2f}%", 
            delta=f"{tnx_change5d:.2f}", 
            delta_color="inverse"
        )
    with col_var1:
        st.metric("Il y a 15j", f"{macro_df['^TNX'].iloc[-15]:.2f}%")
    with col_var2:
        st.metric("Il y a 30j", f"{macro_df['^TNX'].iloc[-30]:.2f}%")

    # 2. Dollar Index
    st.subheader("2. Dollar Index (DXY)", help="Une hausse de la force du Dollar tend à drainer la liquidité des marchés mondiaux. C'est a dire que le dollar devient un refuge pour les investisseurs qui retirent leur argent des actifs risqués.")
    col_main, col_var1, col_var2 = st.columns([2, 1, 1])
    with col_main:
        st.metric(
        label="Force du Dollar (delta 5j)", 
        value=f"{macro_df['DX-Y.NYB'].iloc[-1]:.2f}", 
        delta=f"{dxy_change5d:.2f}", 
        delta_color="inverse"
        )
    with col_var1:
        st.metric("Il y a 15j", f"{macro_df['DX-Y.NYB'].iloc[-15]:.2f}")
    with col_var2:
        st.metric("Il y a 30j", f"{macro_df['DX-Y.NYB'].iloc[-30]:.2f}")

    # 3. SPY/TLT (Risk Appetite)
    st.subheader("3. Appétit pour le risque (SPY/TLT)", help="Un ratio SPY/TLT en hausse indique que les investisseurs préfèrent les actions aux obligations, signe d'un appétit pour le risque (Risk-On). A l'inverse, une baisse du ratio indique une préférence pour les obligations, signe de prudence (Risk-Off).")
    col_main, col_var1, col_var2 = st.columns([2, 1, 1])
    with col_main:
        is_risk_on = ratio_trend5d > 0
        st.metric(
        label="Ratio Actions / Obligations 5j", 
        value=f"{spy_tlt_ratio.iloc[-1]:.2f}", 
        delta="Risk ON" if is_risk_on else "Risk OFF",
        delta_color="normal" if is_risk_on else "off"
        )
    st.line_chart(spy_tlt_ratio.tail(30))

with col2:
    st.header("🔬 Micro & Crypto Flows")

    # 4. Rotation Sectorielle
    st.subheader("4. Tech Rotation (XLK/SPY)", help="Un ratio XLK/SPY en hausse indique que les investisseurs favorisent le secteur technologique par rapport au marché global, signe de confiance et d'appétit pour le risque. A l'inverse, une baisse du ratio suggère une rotation vers des secteurs plus défensifs.")
    col_main, col_var1, col_var2 = st.columns([2, 1, 1])
    with col_main:
        is_risk_on = ratio_trend5d > 0
        st.metric(
        label="Force Relative Tech vs S&P500 (delta 5j)",
        value=f"{xlk_spy_ratio.iloc[-1]:.4f}",
        delta="Tech Leader" if rotation_trend5d > 0 else "Tech Lagging"
        )
    
    # 5. Indicateurs de Volume BTC
    st.subheader("5. Bitcoin KPIs")
    test = btc_df['Close'].iloc[-1] - btc_df['Close'].iloc[-8]
    st.metric("BTC price (7j)", btc_df['Close'].iloc[-1].round(2), round(float( (btc_df['Close'].iloc[-1]-btc_df['Close'].shift(7).iloc[-1])/btc_df['Close'].shift(7).iloc[-1]*100 ),2))
    st.line_chart(btc_df['Close'].tail(7).round(2))
    
    c1, c2, c3 = st.columns(3)
    c1.metric("OBV Trend 5j", obv_trend5d, help="On Balance Volume (Cumul des volumes): Si le prix d'une action stagne ou baisse légèrement, mais que l'OBV monte (divergence), c'est que des institutionnels ramassent le titre discrètement (Accumulation).")
    c2.metric("15j", obv_trend15d)
    c3.metric("30j", obv_trend30d)
    c1.metric("MFI (14)", f"{float(current_mfi):.0f}", help="Money Flow Index, détecte la pression acheteuse ou vendeuse réelle: >80 Surchauffe, <20 Survente")
    # Affiche le metric sans utiliser le paramètre `help` (les tooltips perdent souvent le formatage).
    # On fournit à la place un expander adjacent contenant le texte formaté avec paragraphes et listes.
    c2.metric("Prix vs VWAP", "Bullish" if price_vs_vwap.item() else "Bearish")
    with c2.expander("Détails VWAP — aide"): 
        st.markdown(
            """
Si Prix > VWAP (Volume Weighted Average Price) = Acheteurs en contrôle — c'est une question de psychologie de foule mesurée par le VWAP (Prix Moyen Pondéré par le Volume).

Imaginez que le VWAP de la journée sur une action soit de 100 €. Cela signifie que le prix moyen payé par tout le monde (petits et gros acteurs) depuis l'ouverture est de 100 €.

Si le prix actuel est de 102 € (Au-dessus du VWAP) :

- La majorité des gens qui ont acheté aujourd'hui sont en gain (ils sont "verts").
- Ils sont confiants, ils ne paniquent pas.
- Les vendeurs à découvert (short sellers) sont en perte et peuvent être forcés d'acheter pour se couvrir, ce qui pousse le prix encore plus haut.

Conclusion : Les acheteurs ont la main ("Control"), le chemin de moindre résistance est la hausse.

Si le prix actuel est de 98 € (En dessous du VWAP) :

- L'acheteur moyen du jour perd de l'argent.
- Si le prix remonte à 100 €, ces acheteurs piégés vont souvent revendre pour sortir "breakeven" (ni gain ni perte). Cela crée une résistance.

Conclusion : Les vendeurs dominent.
            """,
            unsafe_allow_html=False,
        )

    # 6. Liquidité Stablecoin
    st.subheader("6. Stablecoins Volume")
    if stable_mcap is not None and not stable_mcap.empty:
        current_liq = stable_mcap.iloc[-1] # Valeur la plus récente
        start_liq = stable_mcap.iloc[-30]    # Valeur il y a 30j
        
        # Calcul du changement en Dollars et en Pourcentage
        change_usd = current_liq - start_liq
        change_pct = (change_usd / start_liq) * 100
        
        st.metric(
            label="Liquidité Totale (6 mois)", 
            value=f"${current_liq/1e9:.2f} B", # Affichage en Milliards
            delta=f"{change_pct:.2f}% ({'Injectée' if change_pct > 0 else 'Retirée'})"
        )
        print(current_liq, start_liq, stable_mcap.iloc)
        # Affichage du graphique de tendance
        st.line_chart(stable_mcap.tail(30)/1e9, color="#00FF00" if change_pct > 0 else "#FF0000")

st.divider()
st.subheader("📝 Résumé de la situation")

score = 0
if tnx_change5d < 0: score += 1
if dxy_change5d < 0: score += 1
if is_risk_on: score += 1
if rotation_trend5d > 0: score += 1
if price_vs_vwap.item(): score += 1

if score >= 4:
    st.success(f"🟢 Feu Vert (Score: {score}/5) : L'environnement est très favorable (Risk-On + Liquidité).")
elif score >= 2:
    st.warning(f"🟡 Neutre (Score: {score}/5) : Marché indécis, attention aux faux signaux.")
else:
    st.error(f"🔴 Feu Rouge (Score: {score}/5) : L'environnement Macro draine la liquidité (Risk-Off).")