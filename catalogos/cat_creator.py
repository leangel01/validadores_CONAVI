import os
import json
import pandas as pd

def generar_reglas_procesos_json(
    ruta_excel: str = "./catalogos/CATALOGO_LINEAS_VALIDAS_17082026.xlsx",
    ruta_salida: str = "./catalogos/reglas_procesos.json"
):
    """
    Lee todas las pestañas del Catálogo Maestro PVS, consolida y limpia
    las combinaciones de reglas y exporta la estructura en reglas_procesos.json.
    """
    if not os.path.exists(ruta_excel):
        raise FileNotFoundError(f"No se encontró el archivo de origen: {ruta_excel}")

    xls = pd.ExcelFile(ruta_excel)
    
    # 1. Leer y concatenar todas las pestañas de modalidades
    dfs = [pd.read_excel(xls, sheet_name=sheet) for sheet in xls.sheet_names]
    master_df = pd.concat(dfs, ignore_index=True)

    # 2. Normalizar textos y valores numéricos
    cols_texto = ['esquema', 'modalidad', 'linea_de_apoyo', 'linea_complementaria']
    for col in cols_texto:
        master_df[col] = master_df[col].fillna('').astype(str).str.strip().str.upper()

    master_df['uma_la'] = master_df['uma_la'].fillna(0).astype(float)
    master_df['uma_lc'] = master_df['uma_lc'].fillna(0).astype(float)

    # 3. Construir la jerarquía indexada por clave compuesta (ESQUEMA|MODALIDAD|LINEA_APOYO)
    lineas_autorizadas = {}

    for _, row in master_df.iterrows():
        esq = row['esquema']
        mod = row['modalidad']
        la = row['linea_de_apoyo']
        uma_la = row['uma_la']
        lc = row['linea_complementaria']
        uma_lc = row['uma_lc']

        clave_jerarquia = f"{esq}|{mod}|{la}"

        # Inicializar el nodo si no existe
        if clave_jerarquia not in lineas_autorizadas:
            lineas_autorizadas[clave_jerarquia] = {
                "uma_la": uma_la,
                "complementarias_permitidas": {}
            }

        # Registrar la línea complementaria si está presente
        if lc:
            lineas_autorizadas[clave_jerarquia]["complementarias_permitidas"][lc] = uma_lc

    # 4. Envolver en el esquema general del JSON de procesos
    contenido_json = {
        "lineas_autorizadas_pvs": lineas_autorizadas
    }

    # 5. Crear directorio si no existe y guardar el archivo JSON
    os.makedirs(os.path.dirname(ruta_salida), exist_ok=True)
    with open(ruta_salida, 'w', encoding='utf-8') as f:
        json.dump(contenido_json, f, ensure_ascii=False, indent=2)

    print(f"✅ Archivo JSON generado exitosamente en: {ruta_salida}")
    print(f"📊 Total de combinaciones jerárquicas procesadas: {len(lineas_autorizadas)}")

if __name__ == "__main__":
    generar_reglas_procesos_json()