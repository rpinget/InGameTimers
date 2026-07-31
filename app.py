import streamlit as st
import requests
import math

# --- DICCIONARIOS BASE ---
SPELL_BASE_CDS = {
    4: {"name": "Flash", "cd": 300}, 12: {"name": "Teleport", "cd": 360},
    14: {"name": "Ignite", "cd": 180}, 3: {"name": "Exhaust", "cd": 210},
    7: {"name": "Heal", "cd": 240}, 6: {"name": "Ghost", "cd": 210},
    21: {"name": "Barrier", "cd": 180}, 1: {"name": "Cleanse", "cd": 210},
    11: {"name": "Smite", "cd": 90}
}
COSMIC_INSIGHT_ID = 8347

REGION_MAP = {
    "Américas": "americas", "Europa": "europe", "Asia": "asia"
}

PLATFORM_MAP = {
    "LAS (Latinoamérica Sur)": "la2", "LAN (Latinoamérica Norte)": "la1",
    "NA (Norteamérica)": "na1", "BR (Brasil)": "br1",
    "EUW (Europa Oeste)": "euw1", "EUNE (Europa Nórdica y Este)": "eun1",
    "TR (Turquía)": "tr1", "RU (Rusia)": "ru",
    "OCE (Oceanía)": "oc1", "JP (Japón)": "jp1",
    "KR (Corea)": "kr", "PH (Filipinas)": "ph2",
    "SG (Singapur)": "sg2", "TH (Tailandia)": "th2",
    "TW (Taiwán)": "tw2", "VN (Vietnam)": "vn2"
}

def calculate_cd(base_cd, has_cosmic):
    return math.floor(base_cd * (100 / (100 + (18 if has_cosmic else 0))))

# --- FUNCIONES CON CACHÉ (CORREGIDAS) ---
# Ahora devolvemos diccionarios simples que Streamlit puede guardar sin fallos.

@st.cache_data(ttl=3600, show_spinner=False)
def get_puuid_data(api_key, region, riot_id, tagline):
    url = f"https://{region}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{riot_id}/{tagline}"
    res = requests.get(url, headers={"X-Riot-Token": api_key})
    if res.status_code == 200:
        return {"status": 200, "puuid": res.json()['puuid']}
    return {"status": res.status_code}

@st.cache_data(ttl=15, show_spinner=False)
def get_live_match_data(api_key, platform, puuid):
    url = f"https://{platform}.api.riotgames.com/lol/spectator/v5/active-games/by-summoner/{puuid}"
    res = requests.get(url, headers={"X-Riot-Token": api_key})
    if res.status_code == 200:
        return {"status": 200, "data": res.json()}
    return {"status": res.status_code}


# --- INTERFAZ ---
st.set_page_config(page_title="LoL CD Tracker", layout="wide")

st.sidebar.title("⚙️ Configuración")
api_key = st.sidebar.text_input("Riot API Key (RGAPI-...)", type="password")

riot_id = st.sidebar.text_input("Riot ID (ej: MiNombre)", "PipiRomagnoli")
tagline = st.sidebar.text_input("Tagline (ej: LAS)", "ALDOG")

selected_region = st.sidebar.selectbox("Región de Cuenta", list(REGION_MAP.keys()))
region = REGION_MAP[selected_region]

selected_platform = st.sidebar.selectbox("Servidor de Juego", list(PLATFORM_MAP.keys()))
platform = PLATFORM_MAP[selected_platform]

st.title("⏱️ Tracker de Summoners - Minuto 0")

if st.button("Buscar Partida en Vivo"):
    if not api_key:
        st.error("Por favor, ingresa tu API Key en la barra lateral.")
    else:
        with st.spinner("Conectando con los servidores de Riot..."):
            
            # 1. Obtener PUUID 
            acc_result = get_puuid_data(api_key, region, riot_id, tagline)
            
            if acc_result["status"] != 200:
                st.error(f"Error en la cuenta. ¿Caducó la API Key? Código: {acc_result['status']}")
            else:
                puuid = acc_result["puuid"]
                
                # 2. Buscar partida (El caché protegerá tu límite si aprietas rápido)
                match_result = get_live_match_data(api_key, platform, puuid)
                
                if match_result["status"] == 404:
                    st.warning("No estás en partida. (El botón está protegido por 15 segundos para no agotar tu API Key).")
                elif match_result["status"] == 429:
                    st.error("Límite de Riot excedido. Espera exactamente 2 minutos y vuelve a intentarlo.")
                elif match_result["status"] != 200:
                    st.error(f"Error buscando la partida. Código: {match_result['status']}")
                else:
                    match_data = match_result["data"]
                    players = []
                    
                    # 3. Procesar jugadores
                    for p in match_data['participants']:
                        perks = p.get('perks', {}).get('perkIds', [])
                        has_cosmic = COSMIC_INSIGHT_ID in perks
                        
                        sp1 = SPELL_BASE_CDS.get(p['spell1Id'], {"name": "Desconocido", "cd": 0})
                        sp2 = SPELL_BASE_CDS.get(p['spell2Id'], {"name": "Desconocido", "cd": 0})
                        
                        players.append({
                            "Equipo": "Azul" if p['teamId'] == 100 else "Rojo",
                            "Jugador": p.get('riotId', p.get('summonerName', 'Bot')),
                            "Hechizo 1": f"{sp1['name']} ({calculate_cd(sp1['cd'], has_cosmic)}s)",
                            "Hechizo 2": f"{sp2['name']} ({calculate_cd(sp2['cd'], has_cosmic)}s)",
                            "Cosmic Insight": "Sí (-18 Haste)" if has_cosmic else "No"
                        })
                        
                    st.table(players)
