

import json
from pathlib import Path

import pandas as pd

from core.base import BaseValidator
from core.common_rules import validar_mayoria_edad, validar_unicidad_curp


class ModificacionesValidator(BaseValidator):
    """Valida datos originales y cambios realizados en una modificación."""

    def __init__(self, df: pd.DataFrame, config: dict = None):
        super().__init__(df, config)
        ruta_reglas = Path(__file__).resolve().parents[2] / 'catalogos' / 'reglas_procesos.json'
        with ruta_reglas.open('r', encoding='utf-8') as archivo:
            self.reglas_procesos = json.load(archivo).get('lineas_autorizadas_pvs', {})

    @staticmethod
    def _texto(valor) -> str:
        if pd.isna(valor):
            return ''
        texto = str(valor).strip().upper()
        return '' if texto == '-' else texto

    @staticmethod
    def _es_sin_cambio(valor) -> bool:
        return pd.isna(valor) or str(valor).strip() in ('', '-')

    @staticmethod
    def _numero(valor) -> float:
        if ModificacionesValidator._es_sin_cambio(valor):
            return 0.0
        try:
            return float(valor)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _formatear_monto(valor) -> str:
        return f'{valor:,.2f}'

    @staticmethod
    def _supera_tope(valor: float, tope: float) -> bool:
        return round(valor, 2) > round(tope, 2)

    def _obtener_regla(self, esquema: str, modalidad: str, linea: str):
        return self.reglas_procesos.get(f'{esquema}|{modalidad}|{linea}')

    @staticmethod
    def _valor_efectivo(original, modificado, es_texto=False):
        sin_cambio = pd.isna(modificado) or str(modificado).strip() in ('', '-')
        if sin_cambio:
            return original
        if es_texto:
            texto = str(modificado).strip().upper()
            return '' if texto == '-' else texto
        try:
            return float(modificado)
        except (TypeError, ValueError):
            return 0.0

    @classmethod
    def _monto_efectivo_complementaria(cls, fila, numero):
        linea_original = fila.get(f'linea_c{numero}', '')
        linea_modificada = fila.get(f'linea_c{numero}_modificado', '')
        monto_original = fila.get(f'monto_linea_c{numero}', 0)
        monto_modificado = fila.get(f'monto_linea_c{numero}_modificado', '')

        if cls._es_sin_cambio(linea_modificada) and cls._es_sin_cambio(monto_modificado):
            return cls._valor_efectivo(monto_original, '')
        return cls._valor_efectivo(monto_original, monto_modificado)

    @staticmethod
    def _agregar_error(df, indice, mensaje):
        df.at[indice, 'observaciones_sistema'] += f'[ERR: {mensaje}] '

    def _validar_curp(self, df):
        curp_original = df['curp'].fillna('').astype(str).str.strip()
        df_original = pd.DataFrame({'curp': curp_original}, index=df.index)
        unicas = validar_unicidad_curp(df_original, 'curp')
        curp_ok, edad_ok = validar_mayoria_edad(df_original, 'curp', self.config.get('edad_minima', 18))
        for indice in df.index:
            if not curp_ok.loc[indice]:
                self._agregar_error(df, indice, 'CURP original inválida')
            elif not edad_ok.loc[indice]:
                self._agregar_error(df, indice, 'Beneficiario de CURP original menor de edad')
            if not unicas.loc[indice]:
                self._agregar_error(df, indice, 'CURP original duplicada')

        curp_nueva = df['curp_modificada'].fillna('').astype(str).str.strip()
        informada = ~curp_nueva.str.upper().isin(('', '-'))
        if not informada.any():
            return
        df_nuevas = pd.DataFrame({'curp': curp_nueva.where(informada, '')}, index=df.index)
        nuevas_unicas = validar_unicidad_curp(df_nuevas, 'curp')
        nuevas_ok, nuevas_edad = validar_mayoria_edad(df_nuevas, 'curp', self.config.get('edad_minima', 18))
        for indice in df.index[informada]:
            if not nuevas_ok.loc[indice]:
                self._agregar_error(df, indice, 'CURP nueva inválida')
            elif not nuevas_edad.loc[indice]:
                self._agregar_error(df, indice, 'Beneficiario de CURP nueva menor de edad')
            if not nuevas_unicas.loc[indice]:
                self._agregar_error(df, indice, 'CURP nueva duplicada')

    def _validar_version(self, fila, indice, df, sufijo, regla):
        monto_apoyo_unico = self._numero(fila.get(f'apoyo_unico{sufijo}', 0))
        monto_linea = self._numero(fila.get(f'monto_linea_apoyo{sufijo}', 0))
        monto_total = self._numero(fila.get(f'monto_total{sufijo}', 0))
        limite_linea = regla.get('uma_la', 0) * self.uma_mensual
        limite_total = regla.get('uma_max', 0) * self.uma_mensual
        complementarias = regla.get('complementarias_permitidas', {})
        suma = monto_apoyo_unico + monto_linea

        if self._supera_tope(monto_linea, limite_linea):
            self._agregar_error(df, indice, f'Monto de línea de apoyo {sufijo or "original"} supera el máximo de {self._formatear_monto(limite_linea)} pesos')

        for numero in range(1, 8):
            nombre = self._texto(fila.get(f'linea_c{numero}{sufijo}', ''))
            monto = self._numero(fila.get(f'monto_linea_c{numero}{sufijo}', 0))
            if not nombre:
                continue
            suma += monto
            maximo_umas = complementarias.get(nombre)
            if maximo_umas is None:
                self._agregar_error(df, indice, f'Línea complementaria no permitida: {nombre}')
            elif self._supera_tope(monto, maximo_umas * self.uma_mensual):
                self._agregar_error(df, indice, f'Monto de {nombre} {sufijo or "original"} supera el máximo de {self._formatear_monto(maximo_umas * self.uma_mensual)} pesos')

        if abs(round(suma - monto_total, 2)) > 0.01:
            self._agregar_error(df, indice, f'La suma de línea de apoyo y complementarias ({self._formatear_monto(suma)}) no coincide con el monto total ({self._formatear_monto(monto_total)})')
        if self._supera_tope(suma, limite_total):
            self._agregar_error(df, indice, f'La suma de línea de apoyo y complementarias supera el máximo de {self._formatear_monto(limite_total)} pesos')

    def _validar_alineacion(self, df, indice, esquema, modalidad, linea, tipo):
        regla = self._obtener_regla(esquema, modalidad, linea)
        if regla is None:
            self._agregar_error(df, indice, f'{tipo} no encontrada en reglas S100: esquema="{esquema or "VACÍO"}", modalidad="{modalidad or "VACÍA"}", línea="{linea or "VACÍA"}"')
        return regla

    def validar_especifico(self, df: pd.DataFrame) -> pd.DataFrame:
        self._validar_curp(df)
        for indice, fila in df.iterrows():
            esquema = self._texto(fila.get('esquema', ''))
            modalidad = self._texto(fila.get('modalidad', ''))
            linea_original = self._texto(fila.get('linea_apoyo', ''))
            regla_original = self._validar_alineacion(df, indice, esquema, modalidad, linea_original, 'Línea de apoyo original')
            if regla_original is None:
                continue
            self._validar_version(fila, indice, df, '', regla_original)

            linea_efectiva = self._valor_efectivo(linea_original, fila.get('linea_apoyo_modificado', ''), es_texto=True)
            regla_efectiva = regla_original
            if linea_efectiva != linea_original:
                regla_efectiva = self._validar_alineacion(df, indice, esquema, modalidad, linea_efectiva, 'Nueva línea de apoyo')
                if regla_efectiva is None:
                    continue

            fila_efectiva = fila.copy()
            fila_efectiva['apoyo_unico_modificado'] = self._valor_efectivo(fila.get('apoyo_unico', 0), fila.get('apoyo_unico_modificado', 0))
            fila_efectiva['monto_total_modificado'] = self._valor_efectivo(fila.get('monto_total', 0), fila.get('monto_total_modificado', 0))
            fila_efectiva['monto_linea_apoyo_modificado'] = self._valor_efectivo(fila.get('monto_linea_apoyo', 0), fila.get('monto_linea_apoyo_modificado', 0))
            for numero in range(1, 8):
                fila_efectiva[f'linea_c{numero}_modificado'] = self._valor_efectivo(fila.get(f'linea_c{numero}', ''), fila.get(f'linea_c{numero}_modificado', ''), es_texto=True)
                fila_efectiva[f'monto_linea_c{numero}_modificado'] = self._monto_efectivo_complementaria(fila, numero)
            self._validar_version(fila_efectiva, indice, df, '_modificado', regla_efectiva)
        return df

    def validar(self) -> pd.DataFrame:
        df_resultado = self.df.copy()
        df_resultado['observaciones_sistema'] = ''
        df_resultado = self.validar_especifico(df_resultado)
        df_resultado['es_valido'] = df_resultado['observaciones_sistema'] == ''
        return df_resultado
