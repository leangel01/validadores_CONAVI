"""
Este módulo contiene validaciones específicas para APROBACIONES.

Combina las reglas comunes con el catálogo de líneas autorizadas para
comprobar montos, líneas de apoyo y líneas complementarias.
"""

import json
from pathlib import Path

import pandas as pd
from core.base import BaseValidator

class AprobacionesValidator(BaseValidator):
    """Valida cada registro conforme a las reglas de aprobaciones."""

    @staticmethod
    def _formatear_monto(valor) -> str:
        return f'{valor:,.2f}'

    @staticmethod
    def _supera_tope(valor: float, tope: float) -> bool:
        return round(valor, 2) > round(tope, 2)

    def __init__(self, df: pd.DataFrame, config: dict = None):
        """Inicializa las reglas comunes y carga el catálogo del proceso."""
        super().__init__(df, config)
        ruta_reglas = Path(__file__).resolve().parents[2] / 'catalogos' / 'reglas_procesos.json'
        with ruta_reglas.open('r', encoding='utf-8') as archivo:
            self.reglas_procesos = json.load(archivo).get('lineas_autorizadas_pvs', {})

    @staticmethod
    def _texto(valor) -> str:
        """Normaliza el texto para compararlo con el catálogo."""
        if pd.isna(valor):
            return ''
        texto = str(valor).strip().upper()
        return '' if texto == '-' else texto

    @staticmethod
    def _numero(valor) -> float:
        """Convierte un importe vacío o marcado con guion en cero."""
        if pd.isna(valor) or str(valor).strip() == '-':
            return 0.0
        return float(valor)

    def _validar_lineas_y_montos(self, df: pd.DataFrame) -> pd.DataFrame:
        """Valida las líneas autorizadas y sus límites monetarios por fila."""
        columnas_complementarias = [f'linea_c{i}' for i in range(1, 7)]

        for indice, fila in df.iterrows():
            esquema = self._texto(fila.get('esquema', ''))
            modalidad = self._texto(fila.get('modalidad', ''))
            linea_apoyo = self._texto(fila.get('linea_apoyo', ''))
            clave = f'{esquema}|{modalidad}|{linea_apoyo}'
            regla = self.reglas_procesos.get(clave)

            # Relaciona cada registro con una regla usando su clave compuesta: {esquema}|{modalidad}|{linea_apoyo}.
            if regla is None:
                df.at[indice, 'observaciones_sistema'] += (
                    '[ERR: Línea de apoyo no encontrada en reglas de proceso] '
                )
                continue

            monto_apoyo = self._numero(fila.get('monto_linea_apoyo', 0))
            monto_apoyo_unico = self._numero(fila.get('apoyo_unico', 0))
            monto_total = monto_apoyo_unico + monto_apoyo
            complementarias = regla.get('complementarias_permitidas', {})
            complementarias_seleccionadas = []

            # Revisa las seis lineas complementarias.
            for columna_linea in columnas_complementarias:
                nombre_linea = self._texto(fila.get(columna_linea, ''))
                monto = self._numero(fila.get(f'monto_{columna_linea}', 0))

                if not nombre_linea:
                    if monto > 0:
                        df.at[indice, 'observaciones_sistema'] += (
                            f'[ERR: Monto asignado sin {columna_linea}] '
                        )
                    continue

                complementarias_seleccionadas.append(nombre_linea)
                monto_total += monto
                maximo = complementarias.get(nombre_linea)
                if maximo is None:
                    df.at[indice, 'observaciones_sistema'] += (
                        f'[ERR: Línea complementaria no permitida: {nombre_linea}] '
                    )
                elif monto <= 0:
                    df.at[indice, 'observaciones_sistema'] += (
                        f'[ERR: Monto requerido para línea complementaria {nombre_linea}] '
                    )
                elif self._supera_tope(monto, maximo * self.uma_mensual):
                    df.at[indice, 'observaciones_sistema'] += (
                    f'[ERR: Monto de {nombre_linea} supera el máximo de '
                    f'{self._formatear_monto(maximo * self.uma_mensual)} pesos ({maximo} UMAs)] '
                    )

            if monto_apoyo <= 0:
                if not complementarias_seleccionadas:
                    df.at[indice, 'observaciones_sistema'] += (
                        '[ERR: Monto de línea de apoyo requerido cuando no hay complementarias] '
                    )
            elif self._supera_tope(monto_apoyo, regla.get('uma_la', 0) * self.uma_mensual):
                df.at[indice, 'observaciones_sistema'] += (
                    f'[ERR: Monto de línea de apoyo supera el máximo de '
                    f'{self._formatear_monto(regla["uma_la"] * self.uma_mensual)} pesos '
                    f'({regla["uma_la"]} UMAs)] '
                )

            if 'monto_aprobado' in df.columns:
                monto_aprobado = self._numero(fila.get('monto_aprobado', 0))
                if complementarias_seleccionadas or monto_apoyo_unico > 0:
                    tope_maximo = regla.get('uma_max', 0) * self.uma_mensual
                    if self._supera_tope(monto_total, tope_maximo):
                        df.at[indice, 'observaciones_sistema'] += (
                            f'[ERR: La suma de línea de apoyo y complementarias supera el máximo de '
                            f'{self._formatear_monto(tope_maximo)} pesos ({regla.get("uma_max", 0)} UMAs)] '
                        )
                    monto_a_comparar = monto_total
                    concepto_monto = 'La suma de línea de apoyo y complementarias'
                else:
                    monto_a_comparar = monto_apoyo
                    concepto_monto = 'El monto de línea de apoyo'

                if abs(monto_a_comparar - monto_aprobado) > 0.01:
                    df.at[indice, 'observaciones_sistema'] += (
                        f'[ERR: {concepto_monto} ({monto_a_comparar:.2f} pesos) '
                        f'no coincide con el monto aprobado '
                        f'({monto_aprobado:.2f} pesos)] '
                    )
            elif complementarias_seleccionadas:
                tope_maximo = regla.get('uma_max', 0) * self.uma_mensual
                if self._supera_tope(monto_total, tope_maximo):
                    df.at[indice, 'observaciones_sistema'] += (
                        f'[ERR: La suma de línea de apoyo y complementarias supera el máximo de '
                        f'{self._formatear_monto(tope_maximo)} pesos ({regla.get("uma_max", 0)} UMAs)] '
                    )

        return df
    
    def validar_especifico(self, df: pd.DataFrame) -> pd.DataFrame:
        """Se ejecutan las reglas exclusivas par la validación de aprobaciones."""
        
        # Valida que exista un monto aprobado positivo.
        if 'monto_aprobado' in df.columns:
            mask_monto = df['monto_aprobado'] > 0
            df.loc[~mask_monto, 'observaciones_sistema'] += '[ERR: Monto aprobado inválido] '

        return self._validar_lineas_y_montos(df)