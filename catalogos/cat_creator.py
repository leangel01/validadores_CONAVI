"""Generador del catálogo JSON de reglas específicas de las lineas de apoyo y sus complementarias.

Se transforma el catálogo en Excel en una estructura JSON que el
validador puede consultar por esquema, modalidad y línea de apoyo.
La información proviene de las tablas donde se definen las líneas autorizadas y sus límites en UMAs.
"""

import os
import json
import pandas as pd

def generar_reglas_procesos_json(
    ruta_excel: str = "./catalogos/CATALOGO_LINEAS_VALIDAS_21082026.xlsx",
    ruta_salida: str = "./catalogos/reglas_procesos.json"
):
    """Aquí se genera el archivo ``reglas_procesos.json`` a partir del catálogo de Excel."""
    if not os.path.exists(ruta_excel):
        raise FileNotFoundError(f"No se encontró el archivo de origen: {ruta_excel}")

    xls = pd.ExcelFile(ruta_excel)
    
    # Se unen todas las pestañas para construir un catálogo único.
    dfs = [pd.read_excel(xls, sheet_name=sheet) for sheet in xls.sheet_names]
    master_df = pd.concat(dfs, ignore_index=True)
    """
    Se normalizan textos y números antes de crear las claves.

    Los nombres de las lineas de apoyo y complementarias se convierten a mayúsculas para coincidir con el 
    formato que contienen los documentos de entrada y se eliminan espacios externos.
    """
    cols_texto = ['esquema', 'modalidad', 'linea_de_apoyo', 'linea_complementaria']
    for col in cols_texto:
        master_df[col] = master_df[col].fillna('').astype(str).str.strip().str.upper()

    master_df['uma_max'] = master_df['uma_max'].fillna(0).astype(float)
    master_df['uma_la'] = master_df['uma_la'].fillna(0).astype(float)
    master_df['uma_lc'] = master_df['uma_lc'].fillna(0).astype(float)

    # Se indexa cada combinación por ESQUEMA|MODALIDAD|LINEA_APOYO.
    lineas_autorizadas = {}

    for _, row in master_df.iterrows():
        esq = row['esquema']
        mod = row['modalidad']
        la = row['linea_de_apoyo']
        uma_max = row['uma_max']
        uma_la = row['uma_la']
        lc = row['linea_complementaria']
        uma_lc = row['uma_lc']

        clave_jerarquia = f"{esq}|{mod}|{la}"

        # Crea el nodo principal la primera vez que encuentro la combinación.
        if clave_jerarquia not in lineas_autorizadas:
            lineas_autorizadas[clave_jerarquia] = {
                "uma_max": uma_max,
                "uma_la": uma_la,
                "complementarias_permitidas": {}
            }

        # Se guarda cada línea complementaria y su límite en UMAs.
        if lc:
            lineas_autorizadas[clave_jerarquia]["complementarias_permitidas"][lc] = uma_lc

    # Se envuelve el índice en la estructura esperada por el validador.
    contenido_json = {
        "lineas_autorizadas_pvs": lineas_autorizadas
    }

    # Se crea el catálogo en formato JSON, dentro de la carpeta de salida.
    os.makedirs(os.path.dirname(ruta_salida), exist_ok=True)
    with open(ruta_salida, 'w', encoding='utf-8') as f:
        json.dump(contenido_json, f, ensure_ascii=False, indent=2)

    print(f"✅ Archivo JSON generado exitosamente en: {ruta_salida}")
    print(f"📊 Total de combinaciones jerárquicas procesadas: {len(lineas_autorizadas)}")

if __name__ == "__main__":
    generar_reglas_procesos_json()