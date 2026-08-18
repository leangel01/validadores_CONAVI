import os
import json
import tkinter as tk
from tkinter import filedialog
import pandas as pd
from typing import Union

class AprobacionesReader:
    def __init__(self, ruta_comunes: str = "catalogos/reglas_comunes.json"):
        if not os.path.exists(ruta_comunes):
            raise FileNotFoundError(f"No se encontró el archivo de reglas comunes: {ruta_comunes}")

        with open(ruta_comunes, 'r', encoding='utf-8') as f:
            config = json.load(f)

        self.mapa_columnas = config.get("mapeo_columnas", {})
        
        # Extraer sinónimos en mayúsculas
        self.sinonimos_catalogos = {
            str(sin).strip().upper()
            for sinonimos in self.mapa_columnas.values()
            for sin in sinonimos
        }

        # Definir claves numéricas basadas exactamente en las 34 del JSON
        self.cols_numericas = [
            "ingresos", "apoyo_unico", "monto_linea_apoyo", "monto_aprobado"
        ] + [f"monto_linea_c{i}" for i in range(1, 7)]

    def _encontrar_y_ajustar_encabezados(self, df_raw: pd.DataFrame) -> pd.DataFrame:
        """
        Localiza la última fila de encabezados antes de que inicien los datos reales.
        """
        fila_header = None

        for idx in range(min(len(df_raw), 30)):
            valores_fila = [str(v).strip().upper() for v in df_raw.iloc[idx].values if pd.notna(v)]
            
            # Revisa si la fila contiene sinónimos del catálogo (como 'NO.')
            tiene_sinonimos = any(val in self.sinonimos_catalogos for val in valores_fila)
            
            if tiene_sinonimos:
                fila_header = idx
            elif fila_header is not None:
                # Si ya habíamos encontrado un encabezado y esta fila no lo es,
                # verificamos si es una fila de datos para detener la búsqueda
                primer_val = str(df_raw.iloc[idx, 0]).strip() if pd.notna(df_raw.iloc[idx, 0]) else ""
                if primer_val != "" and primer_val.upper() != "NO.":
                    break

        if fila_header is not None:
            nuevos_encabezados = [str(col).strip() for col in df_raw.iloc[fila_header].values]
            df = df_raw.iloc[fila_header + 1:].copy()
            df.columns = nuevos_encabezados
            return df.reset_index(drop=True)

        return df_raw

    def _estandarizar_y_filtrar_columnas(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Mapea las columnas al estándar y filtra el DataFrame para mantener
        EXACTAMENTE las 34 columnas del JSON.
        """
        renombrar = {}
        columnas_archivo = [str(col).strip().upper() for col in df.columns]
        df.columns = columnas_archivo

        for std_name, sinonimos in self.mapa_columnas.items():
            for sin in sinonimos:
                sin_clean = str(sin).strip().upper()
                if sin_clean in df.columns:
                    renombrar[sin_clean] = std_name
                    break

        df = df.rename(columns=renombrar)

        # Garantizar que existan las 34 columnas esperadas
        for std_name in self.mapa_columnas.keys():
            if std_name not in df.columns:
                df[std_name] = None

        # Filtrar y ordenar para retornar SOLO las 34 columnas del JSON
        return df[list(self.mapa_columnas.keys())]

    def cargar_y_preparar(self, ruta_archivo: str, nombre_hoja: Union[str, int] = "APROBACIONES") -> pd.DataFrame:
        if not os.path.exists(ruta_archivo):
            raise FileNotFoundError(f"No se encontró el archivo a validar: {ruta_archivo}")

        ext = os.path.splitext(ruta_archivo)[1].lower()

        if ext in ['.xlsx', '.xls']:
            df_raw = pd.read_excel(ruta_archivo, sheet_name=nombre_hoja, header=None)
        elif ext == '.csv':
            df_raw = pd.read_csv(ruta_archivo, encoding='utf-8-sig', header=None)
        else:
            raise ValueError(f"Formato no soportado '{ext}'. Formatos válidos: .xlsx, .xls, .csv")

        # 1. Encontrar la fila del encabezado 'NO.' real
        df = self._encontrar_y_ajustar_encabezados(df_raw)

        # 2. Renombrar y recortar exactamente a las 34 columnas
        df = self._estandarizar_y_filtrar_columnas(df)

        # 3. Eliminar filas vacías o repetidas de encabezados residuales
        df = df.dropna(how='all').reset_index(drop=True)
        if 'no.' in df.columns:
            df = df[df['no.'].astype(str).str.strip().str.upper() != 'NO.'].reset_index(drop=True)

        # 4. Formatear columnas de texto
        cols_texto = [k for k in self.mapa_columnas.keys() if k not in self.cols_numericas]
        for col in cols_texto:
            df[col] = df[col].fillna('').astype(str).str.replace(r'\.0$', '', regex=True).str.strip()

        # 5. Formatear columnas numéricas
        for col in self.cols_numericas:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)

        return df


def seleccionar_archivo() -> str:
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)

    ruta_archivo = filedialog.askopenfilename(
        title="Selecciona el archivo a validar",
        filetypes=[
            ("Archivos soportados", "*.xlsx;*.xls;*.csv"),
            ("Archivos Excel", "*.xlsx;*.xls"),
            ("Archivos CSV", "*.csv"),
            ("Todos los archivos", "*.*")
        ]
    )
    root.destroy()
    return ruta_archivo


if __name__ == "__main__":
    archivo_seleccionado = seleccionar_archivo()

    if not archivo_seleccionado:
        print("No se seleccionó ningún archivo. Operación cancelada.")
    else:
        try:
            reader = ExcelReader(ruta_comunes="catalogos/reglas_comunes.json")
            print(f"Cargando hoja 'APROBACIONES' de: {archivo_seleccionado}...")
            
            df_resultado = reader.cargar_y_preparar(archivo_seleccionado)
            
            print("\n--- Vista previa del DataFrame procesado ---")
            print(df_resultado.head())
            print(f"\nDimensiones finales: {df_resultado.shape} (Filas, Columnas)")
            
        except Exception as e:
            print(f"\n[Error] No se pudo procesar el archivo: {e}")