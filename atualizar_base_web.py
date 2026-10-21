import os
import json
import geopandas as gpd

print("=" * 60)
print("  CLEALCO - ATUALIZADOR DA BASE WEB (MAPA INTERATIVO)")
print("=" * 60)

base_dir = os.path.dirname(os.path.abspath(__file__))
shp_dir = os.path.join(base_dir, "SHP")
out_js = os.path.join(base_dir, "dados_mapa.js")

# 0. Buscar status das coletas no KoboToolbox
coletas_por_armadilha = {}
try:
    import requests, re
    KOBO_TOKEN = "21419ca95379f5336eec89bd4decb2a420628d5b"
    ASSET_UID = "aWa7hibK6XamM3jmd9R737"
    url_kobo = f"https://kf.kobotoolbox.org/api/v2/assets/{ASSET_UID}/data.json"
    print("-> Verificando coletas registradas na nuvem...")
    resp_kobo = requests.get(url_kobo, headers={"Authorization": f"Token {KOBO_TOKEN}"}, timeout=10)
    if resp_kobo.status_code == 200:
        for r in resp_kobo.json().get('results', []):
            p_ref = r.get('ponto_cadastrado', '')
            m = re.match(r'^([A-Za-z0-9]+)\b', p_ref)
            if m:
                arm_code = m.group(1).upper()
                coletas_por_armadilha[arm_code] = {
                    'coletado': True,
                    'data_coleta': str(r.get('data_coleta', '')),
                    'hora_coleta': str(r.get('hora_lancamento', '')),
                    'pressao': str(r.get('pressao', '')),
                    'matricula': str(r.get('matricula', ''))
                }
        print(f"   [OK] {len(coletas_por_armadilha)} armadilha(s) coletada(s) encontrada(s) na nuvem.")
except Exception as e:
    print(f"   [AVISO] Nao foi possivel consultar status na nuvem: {e}")

# 1. Armadilhas de Monitoramento da Mosca
pts_shp = os.path.join(shp_dir, "Armadilhas_Mosca.shp")
if not os.path.exists(pts_shp):
    print(f"[ERRO] Arquivo de armadilhas nao encontrado: {pts_shp}")
    input("\nPressione ENTER para sair...")
    exit(1)

print(f"-> Lendo armadilhas: {os.path.basename(pts_shp)}...")
pts = gpd.read_file(pts_shp, encoding='utf-8').to_crs(epsg=4326)
pts_features = []
for idx, row in pts.iterrows():
    id_val = int(row.get('ID', idx + 1))
    unidade = str(row.get('UNIDADE', '')).strip()
    armadilha = str(row.get('ARMADILHA', '')).strip()
    cod_fa = str(row.get('COD_FA', '')).strip()
    fazenda = str(row.get('FAZENDA', '')).strip()
    ponto_desc = str(row.get('PONTO_DESC', '')).strip()
    
    # Formata COD_FA - FAZENDA (ex: 100474 - FAZENDA POUSO ALEGRE)
    if cod_fa and cod_fa not in ['-', 'nan', 'None']:
        fa_completo = f"{cod_fa} - {fazenda}"
    else:
        fa_completo = fazenda if fazenda not in ['nan', 'None'] else ''

    # Ponto de Referência (Propriedade / Armadilha) a partir de PONTO_DESC
    nome_ponto = ponto_desc if (ponto_desc and ponto_desc not in ['nan', 'None']) else f"{armadilha} ({fa_completo})"

    # Verifica status de coleta vindo do Kobo
    info_col = coletas_por_armadilha.get(armadilha.upper(), {})
    is_coletado = info_col.get('coletado', False)

    pts_features.append({
        'type': 'Feature',
        'geometry': {
            'type': 'Point',
            'coordinates': [round(row.geometry.x, 6), round(row.geometry.y, 6)]
        },
        'properties': {
            'id': id_val,
            'num_ponto': id_val,
            'armadilha': armadilha if armadilha != 'nan' else '',
            'unidade': unidade if (unidade and unidade != 'nan') else 'Clealco',
            'cod_fa': cod_fa if (cod_fa and cod_fa != 'nan') else '',
            'fazenda': fazenda if (fazenda and fazenda != 'nan') else '',
            'fa_completo': fa_completo,
            'ponto_desc': nome_ponto,
            'nome_ponto': nome_ponto,
            'proprietario': fazenda if (fazenda and fazenda != 'nan') else '',
            'propriedade': fa_completo,
            'regiao': unidade if (unidade and unidade != 'nan') else 'Clealco',
            'lat': round(row.geometry.y, 6),
            'lon': round(row.geometry.x, 6),
            'coletado': is_coletado,
            'data_coleta': info_col.get('data_coleta', ''),
            'hora_coleta': info_col.get('hora_coleta', ''),
            'pressao': info_col.get('pressao', ''),
            'matricula': info_col.get('matricula', '')
        }
    })
print(f"   [OK] {len(pts_features)} armadilhas processadas.")

# 2. Perimetros das Fazendas
perim_shp = os.path.join(shp_dir, "PERIMETRO_FAZENDAS.shp")
perim_features = []
if os.path.exists(perim_shp):
    print(f"-> Lendo perimetros: {os.path.basename(perim_shp)}...")
    perim = gpd.read_file(perim_shp).to_crs(epsg=4326)
    # Simplifica para alta performance web (~10m)
    perim['geometry'] = perim.geometry.simplify(0.0001, preserve_topology=True)
    for idx, row in perim.iterrows():
        if row.geometry is not None and not row.geometry.is_empty:
            geom_json = row.geometry.__geo_interface__
            faz = str(row.get('FAZENDA', '')).strip()
            nome = str(row.get('NOME_FAZ', '')).strip()
            perim_features.append({
                'type': 'Feature',
                'geometry': geom_json,
                'properties': {
                    'fazenda': faz if faz != 'nan' else '',
                    'nome': nome if nome != 'nan' else ''
                }
            })
    print(f"   [OK] {len(perim_features)} fazendas/talhoes processados.")
else:
    print(f"   [AVISO] Perimetro de fazendas nao encontrado, mantendo apenas pontos.")

# Salvar dados_mapa.js
print("-> Gravando dados_mapa.js...")
with open(out_js, 'w', encoding='utf-8') as f:
    f.write('const DADOS_PONTOS = ' + json.dumps({'type': 'FeatureCollection', 'features': pts_features}, ensure_ascii=False) + ';\n')
    f.write('const DADOS_PERIMETROS = ' + json.dumps({'type': 'FeatureCollection', 'features': perim_features}, ensure_ascii=False) + ';\n')

tam_mb = os.path.getsize(out_js) / (1024 * 1024)
print(f"[CONCLUIDO] Base web atualizada com sucesso ({tam_mb:.2f} MB)!")
print("=" * 60)
