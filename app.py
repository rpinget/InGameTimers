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

def calculate_cd(base_cd, has_cosmic):
    return math.floor(base_cd * (100 / (100 + (18 if has_cosmic else 0))))

st.set_page_config(page_title="LoL CD Tracker", layout="wide")

# --- BARRA LATERAL PARA CONFIGURACIÓN ---
st.sidebar.title("⚙️ Configuración")
api_key = st.sidebar.text_input("Riot API Key (RGAPI-...)", type="password")
riot_id = st.sidebar.text_input("Riot ID (ej: MiNombre)", "MiNombre")
tagline = st.sidebar.text_input("Tagline (ej: LAS)", "LAS")
region = st.sidebar.selectbox("Región de Cuenta", ["americas", "europe", "asia"])
platform = st.sidebar.selectbox("Servidor de Juego", ["la2", "la1", "na1", "euw1"])

st.title("⏱️ Tracker de Summoners - Minuto 0")

if st.button("Buscar Partida en Vivo"):
    if not api_key:
        st.error("Por favor, ingresa tu API Key en la barra lateral.")
    else:
        headers = {"X-Riot-Token": api_key}
        
        # 1. Obtener PUUID
        acc_url = f"https://{region}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{riot_id}/{tagline}"
        acc_res = requests.get(acc_url, headers=headers)
        
        if acc_res.status_code != 200:
            st.error(f"Error en la cuenta. ¿Caducó la API Key? Código: {acc_res.status_code}")
        else:
            puuid = acc_res.json()['puuid']
            
            # 2. Buscar partida
            spec_url = f"https://{platform}.api.riotgames.com/lol/spectator/v5/active-games/by-summoner/{puuid}"
            spec_res = requests.get(spec_url, headers=headers)
            
            if spec_res.status_code == 404:
                st.warning("No estás en partida en este momento.")
            elif spec_res.status_code != 200:
                st.error(f"Error buscando la partida. Código: {spec_res.status_code}")
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