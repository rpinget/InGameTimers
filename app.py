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

# --- FUNCIONES CON CACHÉ PARA PROTEGER LA API ---

# Guarda el PUUID en memoria por 1 hora (3600 segundos)
@st.cache_data(ttl=3600, show_spinner=False)
def get_puuid(api_key, region, riot_id, tagline):
    url = f"https://{region}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{riot_id}/{tagline}"
    headers = {"X-Riot-Token": api_key}
    return requests.get(url, headers=headers)

# Guarda los datos de la partida por 30 segundos para evitar el spam de clics
@st.cache_data(ttl=30, show_spinner=False)
def get_live_match(api_key, platform, puuid):
    url = f"https://{platform}.api.riotgames.com/lol/spectator/v5/active-games/by-summoner/{puuid}"
    headers = {"X-Riot-Token": api_key}
    return requests.get(url, headers=headers)


# --- INTERFAZ ---
st.set_page_config(page_title="LoL CD Tracker", layout="wide")

st.sidebar.title("⚙️ Configuración")
api_key = st.sidebar.text_input("Riot API Key (RGAPI-...)", type="password")
riot_id = st.sidebar.text_input("Riot ID (ej: MiNombre)", "MiNombre")
tagline = st.sidebar.text_input("Tagline (ej: LAS)", "LAS")

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
            # 1. Obtener PUUID (Cacheado)
            acc_res = get_puuid(api_key, region, riot_id, tagline)
            
            if acc_res.status_code != 200:
                st.error(f"Error en la cuenta. ¿Caducó la API Key? Código: {acc_res.status_code}")
                # Borra el caché de esta función si hubo error para que permita intentar de nuevo al cambiar la key
                get_puuid.clear() 
            else:
                puuid = acc_res.json()['puuid']
                
                # 2. Buscar partida (Cacheado por 30s)
                spec_res = get_live_match(api_key, platform, puuid)
                
                if spec_res.status_code == 404:
                    st.warning("No estás en partida en este momento.")
                    get_live_match.clear() # Limpia el caché si no hay partida para que busque instantáneo cuando empiece
                elif spec_res.status_code != 200:
                    st.error(f"Error buscando la partida. Código: {spec_res.status_code}")
                    get_live_match.clear()
                else:
                    match_data = spec_res.json()
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
