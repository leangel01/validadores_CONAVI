from abc import ABC, abstractmethod
import pandas as pd
from core.common_rules import (
    validar_unicidad_curp,
    validar_mayoria_edad,
    validar_tope_ingresos_uma
)

class BaseValidator(ABC):
    def __init__(self, df: pd.DataFrame, config: dict = None):
        self.df = df.copy()
        self.config = config or {}

    def _ejecutar_validaciones_comunes(self, df_res: pd.DataFrame) -> pd.DataFrame:
        # 1. Unicidad de CURP
        mask_unica = validar_unicidad_curp(df_res, col_curp='curp')
        df_res.loc[~mask_unica, 'observaciones_sistema'] += '[ERR: CURP Duplicada] '

        # 2. CURP Válida y Mayoría de Edad (>= 18)
        edad_min = self.config.get("edad_minima", 18)
        mask_curp_ok, mask_edad_ok = validar_mayoria_edad(df_res, col_curp='curp', edad_minima=edad_min)
        df_res.loc[~mask_curp_ok, 'observaciones_sistema'] += '[ERR: Formato de CURP Inválido] '
        df_res.loc[mask_curp_ok & ~mask_edad_ok, 'observaciones_sistema'] += f'[ERR: Beneficiario menor de {edad_min} años] '

        # 3. Ingresos <= 5 UMAs
        max_umas = self.config.get("max_umas_ingreso", 5.0)
        mask_ingresos = validar_tope_ingresos_uma(df_res, col_ingresos='ingresos', max_umas=max_umas)
        df_res.loc[~mask_ingresos, 'observaciones_sistema'] += f'[ERR: Ingreso supera el tope de {max_umas} UMAs o es 0] '

        return df_res

    def validar(self) -> pd.DataFrame:
        df_res = self.df.copy()
        if 'observaciones_sistema' not in df_res.columns:
            df_res['observaciones_sistema'] = ''

        # 1. Ejecutar validaciones atómicas comunes
        df_res = self._ejecutar_validaciones_comunes(df_res)

        # 2. Ejecutar validaciones específicas del trámite
        df_res = self.validar_especifico(df_res)

        # 3. Bandera general de validez
        df_res['es_valido'] = df_res['observaciones_sistema'] == ''
        return df_res

    @abstractmethod
    def validar_especifico(self, df: pd.DataFrame) -> pd.DataFrame:
        pass