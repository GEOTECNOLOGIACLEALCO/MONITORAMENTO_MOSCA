import os
import requests
import pandas as pd
from datetime import datetime, timezone, timedelta

print("=" * 60)
print("  CLEALCO - EXPORTADOR DE COLETAS EM EXCEL")
print("=" * 60)

KOBO_TOKEN = "21419ca95379f5336eec89bd4decb2a420628d5b"
ASSET_UID = "aWa7hibK6XamM3jmd9R737"
KOBO_SERVER = "kf.kobotoolbox.org"

base_dir = os.path.dirname(os.path.abspath(__file__))
out_xlsx = os.path.join(base_dir, "Coletas_Monitoramento_Mosca.xlsx")

url = f"https://{KOBO_SERVER}/api/v2/assets/{ASSET_UID}/data.json"
headers = {"Authorization": f"Token {KOBO_TOKEN}"}

print(f"-> Conectando ao KoboToolbox...")
resp = requests.get(url, headers=headers)
if resp.status_code != 200:
    print(f"[ERRO] Falha ao conectar: {resp.status_code} - {resp.text}")
    input("\nPressione ENTER para sair...")
    exit(1)

data = resp.json()
results = data.get("results", [])
print(f"-> Total de coletas recebidas da nuvem: {len(results)}")

if not results:
    print("[AVISO] Nenhuma coleta registrada ainda no sistema.")
    input("\nPressione ENTER para sair...")
    exit(0)

# Carregar coordenadas dos pontos de referência
ref_shp = os.path.join(base_dir, "SHP", "Armadilhas_Mosca.shp")
if not os.path.exists(ref_shp):
    ref_shp = os.path.join(base_dir, "SHP", "Pontos_Monitoramento_Mosca.shp")

gdf_ref = None
if os.path.exists(ref_shp):
    try:
        import geopandas as gpd
        gdf_ref = gpd.read_file(ref_shp).to_crs(epsg=4326)
    except Exception:
        pass

# Pasta para armazenar as fotos baixadas
fotos_dir = os.path.join(base_dir, "Fotos_Coletas")
os.makedirs(fotos_dir, exist_ok=True)

rows = []
total_fotos_baixadas = 0

for r in results:
    lat, lon = None, None
    gps_str = r.get("localizacao_gps")
    if gps_str:
        parts = str(gps_str).strip().split()
        if len(parts) >= 2:
            try:
                lat = float(parts[0])
                lon = float(parts[1])
            except Exception:
                pass
    
    if (lat is None or lon is None) and "_geolocation" in r and r["_geolocation"] and r["_geolocation"][0] is not None:
        try:
            lat = float(r["_geolocation"][0])
            lon = float(r["_geolocation"][1])
        except Exception:
            pass

    if (lat is None or lon is None) and r.get("latitude") and r.get("longitude"):
        try:
            lat = float(r.get("latitude"))
            lon = float(r.get("longitude"))
        except Exception:
            pass

    p_ref = str(r.get("ponto_cadastrado", "")).strip()
    if (lat is None or lon is None) and gdf_ref is not None:
        import re
        m = re.search(r'^\s*(\d+)|ponto_?(\d+)|ponto\s*#?(\d+)|#\s*(\d+)', p_ref, re.IGNORECASE)
        if m:
            try:
                num_pto = int(m.group(1) or m.group(2) or m.group(3) or m.group(4))
                col_id = 'ID' if 'ID' in gdf_ref.columns else ('NUM_PONTO' if 'NUM_PONTO' in gdf_ref.columns else None)
                if col_id:
                    match = gdf_ref[gdf_ref[col_id] == num_pto]
                    if len(match) > 0:
                        geom_pt = match.geometry.iloc[0]
                        lon, lat = float(geom_pt.x), float(geom_pt.y)
            except Exception:
                pass

    # Hora em Horário de Brasília (UTC-3)
    hora = str(r.get("hora_lancamento", "")).strip()
    if not hora or hora == "None":
        sub_time = str(r.get("_submission_time", "")).strip()
        if "T" in sub_time:
            try:
                dt_str = sub_time.replace("Z", "+00:00")
                if "+" not in dt_str and "-" not in dt_str[10:]:
                    dt_str += "+00:00"
                dt_utc = datetime.fromisoformat(dt_str)
                dt_local = dt_utc.astimezone(timezone(timedelta(hours=-3)))
                hora = dt_local.strftime("%H:%M:%S")
            except Exception:
                hora = sub_time.split("T")[1].split(".")[0]

    # Obter e baixar anexos de fotos da coleta
    attachments = r.get("_attachments", [])
    sub_id = str(r.get("_id", ""))
    foto_links = {"FOTO_1": "", "FOTO_2": "", "FOTO_3": ""}

    for att in attachments:
        fname = att.get("filename", "")
        dl_url = att.get("download_url", "")
        q_xpath = att.get("question_xpath", "")

        slot = None
        if q_xpath == "foto_1" or "foto_1" in fname or "foto1" in fname:
            slot = "FOTO_1"
        elif q_xpath == "foto_2" or "foto_2" in fname or "foto2" in fname:
            slot = "FOTO_2"
        elif q_xpath == "foto_3" or "foto_3" in fname or "foto3" in fname:
            slot = "FOTO_3"
        elif q_xpath == "foto_armadilha" or "foto_armadilha" in fname:
            slot = "FOTO_1"

        if slot and dl_url:
            local_fname = f"Coleta_{sub_id}_{slot.lower()}.jpg"
            local_fpath = os.path.join(fotos_dir, local_fname)
            
            # Baixa o arquivo para o disco se ainda não tiver sido baixado
            if not os.path.exists(local_fpath) or os.path.getsize(local_fpath) == 0:
                try:
                    img_resp = requests.get(dl_url, headers=headers, timeout=20)
                    if img_resp.status_code == 200:
                        with open(local_fpath, "wb") as f_img:
                            f_img.write(img_resp.content)
                        total_fotos_baixadas += 1
                        print(f"   [FOTO BAIXADA] {local_fname}")
                except Exception as e:
                    print(f"   [AVISO] Falha ao baixar foto {local_fname}: {e}")

            if os.path.exists(local_fpath) and os.path.getsize(local_fpath) > 0:
                # Hiperlink relativo para abrir direto no Excel
                foto_links[slot] = f'=HYPERLINK("Fotos_Coletas\\{local_fname}", "Ver {slot} ({local_fname})")'
            else:
                foto_links[slot] = dl_url

    rows.append({
        "DATA": str(r.get("data_coleta", "")),
        "HORA": hora,
        "PONTO_REFERENCIA": p_ref,
        "FA": str(r.get("fa", "")),
        "PRESSAO": str(r.get("pressao", "")),
        "MATRICULA": str(r.get("matricula", "")),
        "FOTO_1": foto_links["FOTO_1"],
        "FOTO_2": foto_links["FOTO_2"],
        "FOTO_3": foto_links["FOTO_3"],
        "LATITUDE": lat if lat is not None else "",
        "LONGITUDE": lon if lon is not None else "",
        "ID_REGISTRO": sub_id
    })

df = pd.DataFrame(rows)
df.sort_values(by=["DATA", "HORA"], ascending=[False, False], inplace=True)

while True:
    try:
        df.to_excel(out_xlsx, index=False)
        print(f"[CONCLUIDO] Planilha Excel gerada com sucesso:")
        print(f"  -> {out_xlsx}")
        break
    except PermissionError:
        print(f"\n[AVISO] O arquivo '{os.path.basename(out_xlsx)}' esta aberto no Excel!")
        print(f"Por favor, FECHE a planilha no Excel e pressione ENTER para continuar...")
        input()

print("=" * 60)
