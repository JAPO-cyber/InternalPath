import streamlit as st
import pandas as pd
import json
import math
import matplotlib.pyplot as plt

st.title("Conversione da Excel a TopoJSON (Coordinate Geografiche - Bergamo)")

uploaded_file = st.file_uploader("Carica il file Excel", type=["xlsx", "xls"])

if uploaded_file is not None:
    # 1. Lettura e pulizia del file Excel
    df = pd.read_excel(uploaded_file)
    
    # Scala del progetto
    st.subheader("Valore di scala del disegno")
    max_distance = st.slider("Scala per collegare i nodi", 
                               min_value=0.0, max_value=20.0, value=5.0,
                               help="Il GeoJson viene scalato con questo valore per i calcolo dei parametri")
    # Rimuove " m", sostituisce la virgola con il punto e converte in float
    for col in ["X", "Y", "LenX", "LenY"]:
        df[col] = (df[col].astype(str).str.replace(" m", "", regex=False).str.replace(",", ".").astype(float)*max_distance)
        
    # 2. Filtra le righe in cui "Definition Name" è "Macchina" e calcola i vertici del quadrato
    df_macchina = df
    
    def calcola_punti(row):
        x = row["X"]
        y = row["Y"]
        len_x = row["LenX"]
        len_y = row["LenY"]
        # Chiudiamo il poligono aggiungendo di nuovo il primo punto
        return [
            [x, y],
            [x + len_x, y],
            [x + len_x, y + len_y],
            [x, y + len_y],
            [x, y]
        ]
    
    df_macchina["Punti Quadrato"] = df_macchina.apply(calcola_punti, axis=1)
    df_result = df_macchina[["Definition Name", "Punti Quadrato"]].reset_index(drop=True)
    
    # 3. Conversione delle coordinate locali in coordinate geografiche
    # Usiamo Bergamo come riferimento: lat 45.698, lon 9.677
    bergamo_lat = 45.698
    bergamo_lon = 9.677
    
    # Calcola il centro del bbox locale
    all_local_coords = [pt for poly in df_result["Punti Quadrato"] for pt in poly]
    local_xs = [pt[0] for pt in all_local_coords]
    local_ys = [pt[1] for pt in all_local_coords]
    local_bbox = [min(local_xs), min(local_ys), max(local_xs), max(local_ys)]
    center_x = (local_bbox[0] + local_bbox[2]) / 2
    center_y = (local_bbox[1] + local_bbox[3]) / 2
    
    def local_to_geo(pt, center_x, center_y, bergamo_lon, bergamo_lat):
        dx = pt[0] - center_x
        dy = pt[1] - center_y
        # 1 grado di latitudine ~ 111111 m, per la longitudine moltiplichiamo per cos(lat)
        new_lon = bergamo_lon + dx / (111111 * math.cos(math.radians(bergamo_lat)))
        new_lat = bergamo_lat + dy / 111111
        return [new_lon, new_lat]
    
    def convert_polygon(poly, center_x, center_y, bergamo_lon, bergamo_lat):
        return [local_to_geo(pt, center_x, center_y, bergamo_lon, bergamo_lat) for pt in poly]
    
    df_result["Geo_Punti"] = df_result["Punti Quadrato"].apply(
        lambda poly: convert_polygon(poly, center_x, center_y, bergamo_lon, bergamo_lat)
    )
    
    # 4. Costruzione degli archi (in coordinate geografiche) e delle geometrie
    arcs_geo = []    # Lista degli archi: ogni arco è una lista di coordinate [lon, lat]
    geometries = []  # Lista delle geometrie (feature)
    
    for idx, row in df_result.iterrows():
        polygon = row["Geo_Punti"]
        arcs_geo.append(polygon)
        ent_name = row["Entity Description"]
        geom = {
            "type": "Polygon",
            "arcs": [[idx]],
            "id": ent_name,  # Usa l'Entity Description come id
            "properties": {"name": ent_name, "Entity Description": ent_name}
        }
        geometries.append(geom)
    
    # 5. Calcola il bounding box in coordinate geografiche
    all_geo_coords = [pt for arc in arcs_geo for pt in arc]
    geo_xs = [pt[0] for pt in all_geo_coords]
    geo_ys = [pt[1] for pt in all_geo_coords]
    bbox = [min(geo_xs), min(geo_ys), max(geo_xs), max(geo_ys)]
    
    # 6. Quantizzazione e Delta Encoding
    Q = 10000  # Valore di quantizzazione
    scale_x = (bbox[2] - bbox[0]) / (Q - 1) if Q > 1 else 1
    scale_y = (bbox[3] - bbox[1]) / (Q - 1) if Q > 1 else 1
    transform = {"scale": [scale_x, scale_y], "translate": [bbox[0], bbox[1]]}
    
    def quantize_point(pt, translate, scale):
        return [
            round((pt[0] - translate[0]) / scale[0]),
            round((pt[1] - translate[1]) / scale[1])
        ]
    
    quantized_arcs = []
    for arc in arcs_geo:
        qpoints = [quantize_point(pt, transform["translate"], transform["scale"]) for pt in arc]
        if not qpoints:
            quantized_arcs.append([])
        else:
            delta_arc = [qpoints[0]]
            for i in range(1, len(qpoints)):
                delta = [
                    qpoints[i][0] - qpoints[i-1][0],
                    qpoints[i][1] - qpoints[i-1][1]
                ]
                delta_arc.append(delta)
            quantized_arcs.append(delta_arc)
    
    # 7. Assemblaggio del TopoJSON
    topojson = {
        "type": "Topology",
        "transform": transform,
        "bbox": bbox,
        "objects": {
            "limits_IT_provinces": {
                "type": "GeometryCollection",
                "geometries": geometries
            }
        },
        "arcs": quantized_arcs
    }
    
    # Mostra l'anteprima del TopoJSON
    st.subheader("Anteprima del TopoJSON generato")
    st.json(topojson)
    
    # 8. Visualizzazione con Matplotlib per verifica
    def delta_decode(arc):
        if not arc:
            return []
        decoded = [arc[0]]
        for delta in arc[1:]:
            prev = decoded[-1]
            decoded.append([prev[0] + delta[0], prev[1] + delta[1]])
        return decoded
    
    def invert_quantization(qpt, translate, scale):
        return [
            translate[0] + qpt[0]*scale[0],
            translate[1] + qpt[1]*scale[1]
        ]
    
    fig, ax = plt.subplots(figsize=(8, 6))
    for geom in topojson["objects"]["limits_IT_provinces"]["geometries"]:
        polygon_coords = []
        for arc_indices in geom["arcs"]:
            for idx in arc_indices:
                arc_delta = topojson["arcs"][idx]
                qpoints = delta_decode(arc_delta)
                points = [invert_quantization(qpt, transform["translate"], transform["scale"]) for qpt in qpoints]
                polygon_coords.extend(points)
        # Assicura che il poligono sia chiuso
        if polygon_coords[0] != polygon_coords[-1]:
            polygon_coords.append(polygon_coords[0])
        xs, ys = zip(*polygon_coords)
        ax.plot(xs, ys, marker='o', label=geom["properties"]["name"])
        ax.fill(xs, ys, alpha=0.3)
    ax.set_title("Visualizzazione dei Quadrati Geografici")
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_aspect('equal')
    ax.legend()
    st.pyplot(fig)
    
    # 9. Pulsante per scaricare il TopoJSON
    topojson_str = json.dumps(topojson, ensure_ascii=False, indent=2)
    st.download_button("Scarica il file TopoJSON", data=topojson_str, file_name="quadrati_geo.topo.json", mime="application/json")
else:
    st.info("Carica un file Excel per iniziare.")

