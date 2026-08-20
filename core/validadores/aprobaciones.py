import json
from pathlib import Path

import pandas as pd
from core.base import BaseValidator

class AprobacionesValidator(BaseValidator):

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
    def _numero(valor) -> float:
        if pd.isna(valor) or str(valor).strip() == '-':
            return 0.0
        return float(valor)

    def _validar_lineas_y_montos(self, df: pd.DataFrame) -> pd.DataFrame:
        columnas_complementarias = [f'linea_c{i}' for i in range(1, 7)]

        for indice, fila in df.iterrows():
            esquema = self._texto(fila.get('esquema', ''))
            modalidad = self._texto(fila.get('modalidad', ''))
            linea_apoyo = self._texto(fila.get('linea_apoyo', ''))
            clave = f'{esquema}|{modalidad}|{linea_apoyo}'
            regla = self.reglas_procesos.get(clave)

            if regla is None:
                df.at[indice, 'observaciones_sistema'] += (
                    '[ERR: Línea de apoyo no encontrada en reglas de proceso] '
                )
                continue

            monto_apoyo = self._numero(fila.get('monto_linea_apoyo', 0))
            complementarias = regla.get('complementarias_permitidas', {})
            complementarias_seleccionadas = []

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
                maximo = complementarias.get(nombre_linea)
                if maximo is None:
                    df.at[indice, 'observaciones_sistema'] += (
                        f'[ERR: Línea complementaria no permitida: {nombre_linea}] '
                    )
                elif monto <= 0:
                    df.at[indice, 'observaciones_sistema'] += (
                        f'[ERR: Monto requerido para línea complementaria {nombre_linea}] '
                    )
                elif monto > maximo * self.uma_mensual:
                    df.at[indice, 'observaciones_sistema'] += (
                    f'[ERR: Monto de {nombre_linea} supera el máximo de '
                    f'{maximo * self.uma_mensual:.2f} pesos ({maximo} UMAs)] '
                    )

            if monto_apoyo <= 0:
                if not complementarias_seleccionadas:
                    df.at[indice, 'observaciones_sistema'] += (
                        '[ERR: Monto de línea de apoyo requerido cuando no hay complementarias] '
                    )
            elif monto_apoyo > regla.get('uma_la', 0) * self.uma_mensual:
                df.at[indice, 'observaciones_sistema'] += (
                    f'[ERR: Monto de línea de apoyo supera el máximo de '
                    f'{regla["uma_la"] * self.uma_mensual:.2f} pesos '
                    f'({regla["uma_la"]} UMAs)] '
                )

        return df
    
    def validar_especifico(self, df: pd.DataFrame) -> pd.DataFrame:
        """Reglas exclusivas del trámite de Aprobaciones."""
        
        # Ejemplo: Monto aprobado mayor a 0
        if 'monto_aprobado' in df.columns:
            mask_monto = df['monto_aprobado'] > 0
            df.loc[~mask_monto, 'observaciones_sistema'] += '[ERR: Monto aprobado inválido] '

        return self._validar_lineas_y_montos(df)