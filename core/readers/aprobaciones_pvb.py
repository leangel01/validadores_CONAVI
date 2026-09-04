"""Lector del layout de aprobaciones del esquema PVB.

Convierte la hoja ``MODIFICACIONES`` de la plantilla PVB en un
``DataFrame`` con nombres y tipos uniformes. La plantilla utiliza dos filas
de encabezados: una para agrupar las líneas de apoyo y otra para nombrar cada
columna.
"""

import json
import os
import unicodedata
from typing import Union

import pandas as pd


class AprobacionesPVBReader:
    """Lee y normaliza la hoja de aprobaciones de la plantilla PVB."""

    def __init__(self, ruta_comunes: str = "catalogos/reglas_comunes.json"):
        """Carga el mapeo de columnas esperado por el layout PVB."""
        if not os.path.exists(ruta_comunes):
            raise FileNotFoundError(f"No se encontró el archivo de reglas comunes: {ruta_comunes}")

        with open(ruta_comunes, "r", encoding="utf-8") as archivo:
            config = json.load(archivo)

        self.mapa_columnas = config.get("cols_aprobaciones_pvb", {})
        self.cols_numericas = [
            "total_viviendas",
            *[
                nombre
                for nombre in self.mapa_columnas
                if nombre.startswith("monto_") or nombre == "total_monto_aprobado"
            ],
        ]

    @staticmethod
    def _texto(valor: object) -> str:
        """Convierte una celda de encabezado en texto normalizado."""
        if pd.isna(valor):
            return ""
        return str(valor).strip()

    @staticmethod
    def _sin_acentos(valor: str) -> str:
        """Normaliza acentos para comparar marcas de control del encabezado."""
        return "".join(
            caracter
            for caracter in unicodedata.normalize("NFD", valor)
            if unicodedata.category(caracter) != "Mn"
        )

    def _construir_encabezados(self, df_raw: pd.DataFrame) -> list[str]:
        """Concatena las filas 2 y 3 hasta la columna de aprobación."""
        if len(df_raw) < 3:
            raise ValueError("La hoja APROBACIONES no contiene las filas de encabezados requeridas.")

        grupos = df_raw.iloc[1]
        nombres = df_raw.iloc[2]
        encabezados = []
        grupo_actual = ""
        encontro_grupo = False

        for grupo, nombre in zip(grupos, nombres):
            grupo = self._texto(grupo)
            nombre = self._texto(nombre)

            if grupo:
                grupo_actual = grupo
                encontro_grupo = True

            if not encontro_grupo:
                encabezados.append(nombre)
                continue

            encabezado = f"{grupo_actual}_{nombre}" if grupo_actual and nombre else grupo_actual or nombre
            encabezados.append(encabezado)

            grupo_control = self._sin_acentos(grupo).upper()
            encabezado_control = self._sin_acentos(encabezado).upper()
            if grupo_control == "APROBACION" or encabezado_control.startswith("APROBACION_"):
                break

        if not any(
            self._sin_acentos(encabezado).upper() == "APROBACION_MONTO TOTAL APROBADO ($)"
            for encabezado in encabezados
        ):
            raise ValueError("No se encontró la columna de aprobación en la fila de encabezados.")

        return encabezados

    def _homologar_columnas(self, df: pd.DataFrame) -> pd.DataFrame:
        """Homologa las columnas y verifica que el layout requerido esté completo."""
        df = df.copy()
        df.columns = [str(columna).strip().upper() for columna in df.columns]
        renombrar = {}

        for nombre_estandar, sinonimos in self.mapa_columnas.items():
            for sinonimo in sinonimos:
                sinonimo_limpio = str(sinonimo).strip().upper()
                if sinonimo_limpio in df.columns:
                    renombrar[sinonimo_limpio] = nombre_estandar
                    break

        df = df.rename(columns=renombrar)
        faltantes = [nombre for nombre in self.mapa_columnas if nombre not in df.columns]
        if faltantes:
            raise ValueError(
                "No se encontraron las siguientes columnas necesarias: "
                + ", ".join(faltantes)
            )

        return df[list(self.mapa_columnas)]

    def cargar_y_preparar(
        self,
        ruta_archivo: str,
        nombre_hoja: Union[str, int] = "APROBACIONES",
    ) -> pd.DataFrame:
        """Lee, limpia y normaliza la hoja APROBACIONES de un archivo Excel."""
        if not os.path.exists(ruta_archivo):
            raise FileNotFoundError(f"No se encontró el archivo a validar: {ruta_archivo}")
        if os.path.splitext(ruta_archivo)[1].lower() not in (".xlsx", ".xls", ".xlsm"):
            raise ValueError("Formato no soportado. El lector PVB requiere un archivo Excel.")

        with pd.ExcelFile(ruta_archivo) as archivo_excel:
            hoja_buscada = str(nombre_hoja).strip().casefold()
            hoja_real = next(
                (hoja for hoja in archivo_excel.sheet_names if hoja.strip().casefold() == hoja_buscada),
                None,
            )
            if hoja_real is None:
                raise ValueError(
                    f'No se encontró la hoja "{nombre_hoja}" en el archivo seleccionado.\n'
                )
            df_raw = pd.read_excel(archivo_excel, sheet_name=hoja_real, header=None)

        encabezados = self._construir_encabezados(df_raw)
        df = df_raw.iloc[3:, :len(encabezados)].copy()
        df.columns = encabezados
        df = self._homologar_columnas(df)
        df = df.dropna(how="all").reset_index(drop=True)

        df["no."] = pd.to_numeric(df["no."], errors="coerce")
        df = df[df["no."].notna()].reset_index(drop=True)

        cols_texto = [col for col in self.mapa_columnas if col not in self.cols_numericas]
        for columna in cols_texto:
            df[columna] = (
                df[columna].fillna("").astype(str).str.replace(r"\.0$", "", regex=True).str.strip()
            )
        for columna in self.cols_numericas:
            df[columna] = pd.to_numeric(df[columna], errors="coerce").fillna(0.0)
        #df.to_excel("resultado.xlsx", index=False)  # Guardar el DataFrame en un archivo Excel
        return df


def seleccionar_archivo_pvb() -> str:
    """Muestra el diálogo para seleccionar una plantilla Excel PVB."""
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    ruta_archivo = filedialog.askopenfilename(
        title="Selecciona la plantilla Excel de aprobaciones PVB",
        filetypes=[("Archivos de Excel", "*.xlsx;*.xls;*.xlsm"), ("Todos los archivos", "*.*")],
    )
    root.destroy()
    return ruta_archivo