"""Clase base para coordinar las validaciones comunes y específicas.

Define el orden de validación que deben seguir todos los trámites:
primero las reglas generales (common_rules), después las reglas propias (validadores específicos) y finalmente la
bandera que resume si cada fila es válida.
"""

from abc import ABC, abstractmethod
import json
from pathlib import Path

import pandas as pd
from core.common_rules import (
    validar_unicidad_curp,
    validar_mayoria_edad,
    validar_tope_ingresos_uma
)

class BaseValidator(ABC):
    """Se proporciona la estructura común para todos los validadores."""
    
    def __init__(self, df: pd.DataFrame, config: dict = None):
        """Se guarda una copia de los datos y carga la configuración común."""
        self.df = df.copy()
        self.config = config or {}
        ruta_reglas = Path(__file__).resolve().parents[1] / 'catalogos' / 'reglas_comunes.json'
        with ruta_reglas.open('r', encoding='utf-8') as archivo:
            self.reglas_comunes = json.load(archivo)
        self.uma_mensual = self.reglas_comunes['uma_vigente']['mensual']

    def _ejecutar_validaciones_comunes(self, df_res: pd.DataFrame) -> pd.DataFrame:
        """Se agregan a cada fila los errores de las reglas generales."""

        # Se verifica que ninguna CURP válida aparezca repetida.
        mask_unica = validar_unicidad_curp(df_res, col_curp='curp')
        df_res.loc[~mask_unica, 'observaciones_sistema'] += '[ERR: CURP Duplicada] '

        # Se valida la fecha de la CURP y la edad mínima configurada.
        edad_min = self.config.get("edad_minima", 18)
        mask_curp_ok, mask_edad_ok = validar_mayoria_edad(df_res, col_curp='curp', edad_minima=edad_min)
        df_res.loc[~mask_curp_ok, 'observaciones_sistema'] += '[ERR: Formato de CURP Inválido] '
        df_res.loc[mask_curp_ok & ~mask_edad_ok, 'observaciones_sistema'] += f'[ERR: Beneficiario menor de {edad_min} años] '

        # Se comprueba que el ingreso sea positivo incluyendo cero y esté dentro del límite.
        # El valor de la UMA se obtiene del catálogo de reglas comunes.
        max_umas = self.config.get(
            "max_umas_ingreso",
            self.reglas_comunes['topes_elegibilidad']['max_umas_ingreso_mensual']
        )
        mask_ingresos = validar_tope_ingresos_uma(
            df_res,
            col_ingresos='ingresos',
            max_umas=max_umas,
            uma_mensual=self.uma_mensual
        )
        df_res.loc[~mask_ingresos, 'observaciones_sistema'] += f'[ERR: Ingreso supera el tope de {max_umas} UMAs] '

        return df_res

    def validar(self) -> pd.DataFrame:
        """Ejecuta todas las reglas de validación comunes y específicas, devolviendo el resultado."""
        df_res = self.df.copy()
        if 'observaciones_sistema' not in df_res.columns:
            df_res['observaciones_sistema'] = ''

        # Se ejecutan primero las reglas que comparten todos los procesos.
        df_res = self._ejecutar_validaciones_comunes(df_res)

        # Se delegan las reglas particulares en la clase hija.
        df_res = self.validar_especifico(df_res)

        # Se marca una fila como válida solo cuando no acumuló observaciones.
        df_res['es_valido'] = df_res['observaciones_sistema'] == ''
        return df_res

    @abstractmethod
    def validar_especifico(self, df: pd.DataFrame) -> pd.DataFrame:
        """Se obliga a cada trámite a definir sus reglas particulares."""
        pass