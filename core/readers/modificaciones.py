"""Lector del layout de modificaciones"""

import json
import os
import re
from typing import Union

import pandas as pd


class ModificacionesReader:
    """Lee únicamente las columnas configuradas para modificaciones S100."""

    def __init__(self, ruta_comunes: str = "catalogos/reglas_comunes.json"):
        if not os.path.exists(ruta_comunes):
            raise FileNotFoundError(f"No se encontró el archivo de reglas comunes: {ruta_comunes}")

        with open(ruta_comunes, 'r', encoding='utf-8') as archivo:
            config = json.load(archivo)

        self.mapa_columnas = config.get('cols_modificaciones_S100', {})
        self.homologacion_esquemas = {
            str(opcion).strip().upper(): str(esquema).strip().upper()
            for esquema, opciones in config.get('homologacion_esquemas', {}).items()
            for opcion in opciones
        }
        self.reporte_homologacion = pd.DataFrame(
            columns=['columna', 'original', 'homologado', 'cantidad_ajustes']
        )
        self.sinonimos_catalogos = {
            str(sinonimo).strip().upper()
            for sinonimos in self.mapa_columnas.values()
            for sinonimo in sinonimos
        }
        self.cols_numericas = [
            nombre for nombre in self.mapa_columnas
            if nombre.startswith('monto_') or nombre in ('apoyo_unico', 'apoyo_unico_modificado')
        ]

    @staticmethod
    def _es_columna_complementaria(nombre: str) -> bool:
        """Identifica las columnas opcionales de las líneas complementarias."""
        return re.fullmatch(
            r'(?:linea|monto_linea)_c[1-7](?:_modificado)?',
            nombre,
        ) is not None

    def _encontrar_y_ajustar_encabezados(self, df_raw: pd.DataFrame) -> pd.DataFrame:
        fila_header = None
        for indice in range(min(len(df_raw), 30)):
            valores_fila = [
                str(valor).strip().upper()
                for valor in df_raw.iloc[indice].values
                if pd.notna(valor)
            ]
            if any(valor in self.sinonimos_catalogos for valor in valores_fila):
                fila_header = indice
            elif fila_header is not None:
                primer_valor = (
                    str(df_raw.iloc[indice, 0]).strip()
                    if pd.notna(df_raw.iloc[indice, 0]) else ''
                )
                if primer_valor and primer_valor.upper() != 'NO.':
                    break

        if fila_header is None:
            return df_raw
        encabezados = [str(columna).strip() for columna in df_raw.iloc[fila_header].values]
        df = df_raw.iloc[fila_header + 1:].copy()
        df.columns = encabezados
        return df.reset_index(drop=True)

    def _estandarizar_y_filtrar_columnas(self, df: pd.DataFrame) -> pd.DataFrame:
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

        columnas_faltantes = [
            nombre for nombre in self.mapa_columnas
            if nombre not in df.columns and not self._es_columna_complementaria(nombre)
        ]
        if columnas_faltantes:
            raise ValueError(
                'No se encontraron las siguientes columnas necesarias: '
                + ', '.join(columnas_faltantes)
            )

        for nombre_estandar in self.mapa_columnas:
            if nombre_estandar not in df.columns:
                df[nombre_estandar] = None
        return df[list(self.mapa_columnas)]

    def cargar_y_preparar(
        self,
        ruta_archivo: str,
        nombre_hoja: Union[str, int] = 'MODIFICACIONES',
    ) -> pd.DataFrame:
        if not os.path.exists(ruta_archivo):
            raise FileNotFoundError(f"No se encontró el archivo a validar: {ruta_archivo}")
        extension = os.path.splitext(ruta_archivo)[1].lower()
        if extension in ['.xlsx', '.xls']:
            try:
                with pd.ExcelFile(ruta_archivo) as archivo_excel:
                    hoja_requerida = str(nombre_hoja).casefold()
                    nombre_hoja_real = next(
                        (
                            nombre
                            for nombre in archivo_excel.sheet_names
                            if nombre.strip().casefold() == hoja_requerida
                        ),
                        None,
                    )
                    if nombre_hoja_real is None:
                        raise ValueError(
                            'No se encontró la hoja "MODIFICACIONES", por favor renómbrela en el archivo de origen.\n'
                        )
                    df_raw = pd.read_excel(archivo_excel, sheet_name=nombre_hoja_real, header=None)
            except ValueError as error:
                if str(error).startswith('No se encontró la hoja') or 'Worksheet named' in str(error) or 'not found' in str(error):
                    raise ValueError(
                        'No se encontró la hoja "MODIFICACIONES", por favor renómbrela en el archivo de origen.\n'
                    ) from error
                raise
        elif extension == '.csv':
            df_raw = pd.read_csv(ruta_archivo, encoding='utf-8-sig', header=None)
        else:
            raise ValueError(f"Formato no soportado '{extension}'. Formatos válidos: .xlsx, .xls, .csv")

        df = self._estandarizar_y_filtrar_columnas(
            self._encontrar_y_ajustar_encabezados(df_raw)
        )
        df = df.dropna(how='all').reset_index(drop=True)
        df = df[df['no.'].astype(str).str.strip().str.upper() != 'NO.'].reset_index(drop=True)
        cols_texto = [columna for columna in self.mapa_columnas if columna not in self.cols_numericas]
        for columna in cols_texto:
            df[columna] = (
                df[columna].fillna('').astype(str)
                .str.replace(r'\.0$', '', regex=True).str.strip()
            )
        if 'esquema' in df.columns:
            valores_originales = df['esquema'].copy()
            valores_homologados = valores_originales.str.upper().replace(self.homologacion_esquemas)
            cambios = valores_originales != valores_homologados
            if cambios.any():
                self.reporte_homologacion = (
                    pd.DataFrame({
                        'columna': 'esquema',
                        'original': valores_originales[cambios],
                        'homologado': valores_homologados[cambios],
                    })
                    .groupby(['columna', 'original', 'homologado'], dropna=False)
                    .size()
                    .reset_index(name='cantidad_ajustes')
                )
            df['esquema'] = valores_homologados
        for columna in self.cols_numericas:
            valores = df[columna].astype(object)
            if columna.endswith('_modificado'):
                es_sin_cambio = valores.astype(str).str.strip().eq('-')
                valores_convertidos = pd.to_numeric(valores, errors='coerce').fillna(0.0)
                df[columna] = valores_convertidos.astype(object)
                df.loc[es_sin_cambio, columna] = '-'
            else:
                df[columna] = pd.to_numeric(valores, errors='coerce').fillna(0.0)
        return df