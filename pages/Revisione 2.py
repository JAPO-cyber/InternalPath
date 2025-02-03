# Funzione già esistente per filtrare i corridoi in base a Size
def filtra_corridoi_per_size(machine_idx, corridor_indices):
    """
    Ritorna i corridoi 'validi' in base al valore di 'Size' della macchina.
    Se Size = 'Sinistro', ritorna i corridoi con cx < mx, ecc.
    Se Size è vuoto/NaN, non si applica il filtro (tutti validi).
    """
    size_val = G.nodes[machine_idx]["size"]
    mx, my = G.nodes[machine_idx]["x"], G.nodes[machine_idx]["y"]

    if pd.isna(size_val) or size_val.strip() == "":
        return corridor_indices

    filtered = []
    for c_idx in corridor_indices:
        cx, cy = G.nodes[c_idx]["x"], G.nodes[c_idx]["y"]

        if size_val == "Sinistro" and cx < mx:
            filtered.append(c_idx)
        elif size_val == "Destro" and cx > mx:
            filtered.append(c_idx)
        elif size_val == "Alto" and cy > my:
            filtered.append(c_idx)
        elif size_val == "Basso" and cy < my:
            filtered.append(c_idx)
        # Se Size contiene un valore non previsto, non si filtra
    return filtered

# Nuova funzione per scegliere il corridoio di connessione per la macchina
def choose_corridor(machine_idx, corridor_indices):
    """
    Se per la macchina (machine_idx) è specificata una direzione (Size),
    sceglie il corridoio che massimizza lo scostamento nella direzione desiderata.
    In caso di Size non specificato (o se nessun corridoio soddisfa la condizione),
    sceglie il corridoio con distanza euclidea minima.
    Ritorna una tupla (corridor_idx, distanza).
    """
    size_val = G.nodes[machine_idx]["size"]

    # Se Size non è specificato: fallback su distanza minima
    if pd.isna(size_val) or size_val.strip() == "":
        best_corr = None
        best_dist = float("inf")
        for c in corridor_indices:
            d = distance(machine_idx, c)
            if d < best_dist:
                best_dist = d
                best_corr = c
        return best_corr, best_dist

    # Applichiamo il filtro direzionale
    candidates = filtra_corridoi_per_size(machine_idx, corridor_indices)
    if not candidates:
        # Se non ci sono candidati in direzione corretta, si considera il fallback
        candidates = corridor_indices

    # Se la direzione è specificata, scegliamo in base allo scostamento
    if size_val == "Sinistro":
        best_corr = None
        best_value = -float("inf")
        for c in candidates:
            diff = G.nodes[machine_idx]["x"] - G.nodes[c]["x"]  # positivo se c è a sinistra
            if diff > best_value:
                best_value = diff
                best_corr = c
    elif size_val == "Destro":
        best_corr = None
        best_value = -float("inf")
        for c in candidates:
            diff = G.nodes[c]["x"] - G.nodes[machine_idx]["x"]  # positivo se c è a destra
            if diff > best_value:
                best_value = diff
                best_corr = c
    elif size_val == "Alto":
        best_corr = None
        best_value = -float("inf")
        for c in candidates:
            diff = G.nodes[c]["y"] - G.nodes[machine_idx]["y"]  # positivo se c è sopra
            if diff > best_value:
                best_value = diff
                best_corr = c
    elif size_val == "Basso":
        best_corr = None
        best_value = -float("inf")
        for c in candidates:
            diff = G.nodes[machine_idx]["y"] - G.nodes[c]["y"]  # positivo se c è sotto
            if diff > best_value:
                best_value = diff
                best_corr = c
    else:
        # In caso di valore inatteso, si usa il criterio distanza minima
        best_corr = None
        best_dist = float("inf")
        for c in candidates:
            d = distance(machine_idx, c)
            if d < best_dist:
                best_dist = d
                best_corr = c
        return best_corr, best_dist

    # Calcoliamo la distanza per completezza (per l'attributo weight)
    best_dist = distance(machine_idx, best_corr)
    return best_corr, best_dist

# ---- Modifica nel ciclo di collegamento macchina-corridoio ----
for idx_m in df_macchina.index:
    # Usa la funzione che sceglie in base al criterio direzionale (se presente)
    best_corr, best_dist = choose_corridor(idx_m, corr_indices)
    if best_corr is not None:
        # Collegamento macchina-corridoio con weight = best_dist
        G.add_edge(idx_m, best_corr, weight=best_dist)

