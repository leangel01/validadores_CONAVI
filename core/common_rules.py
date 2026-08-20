"""Reglas que pueden reutilizarse en distintos procesos.

Se concentran aquí las comprobaciones de CURP, edad e ingresos para que cada
validador específico no tenga que duplicarlas.
"""

import pandas as pd
from datetime import datetime
from typing import Tuple

# Este valor de la UMA es una referencia de respaldo por si otro módulo no proporciona el valor.
UMA_MENSUAL_DEFAULT =  3566.22

def extraer_fecha_nacimiento_curp(curp: str) -> Tuple[datetime, bool]:
    """
    Se extrae la fecha de nacimiento a partir de la CURP.
    También se valida su longitud.
    """
    try:
        curp = str(curp).strip().upper()
        if len(curp) != 18:
            return None, False

        yy = int(curp[4:6])
        mm = int(curp[6:8])
        dd = int(curp[8:10])

        anio_actual_corto = int(datetime.now().strftime("%y"))
        siglo = 2000 if yy <= anio_actual_corto else 1900
        
        return datetime(siglo + yy, mm, dd), True
    except Exception:
        return None, False

def validar_unicidad_curp(df: pd.DataFrame, col_curp: str = 'curp') -> pd.Series:
    """Marca como válidas las CURP que no aparecen repetidas."""
    if col_curp not in df.columns:
        return pd.Series(True, index=df.index)
    
    curps = df[col_curp].astype(str).str.strip().str.upper()
    es_duplicado = curps.duplicated(keep=False) & (curps != '')
    return ~es_duplicado

def validar_mayoria_edad(df: pd.DataFrame, col_curp: str = 'curp', edad_minima: int = 18) -> Tuple[pd.Series, pd.Series]:
    """Se comprueba que cada CURP cumpla la edad mínima.

    Devuelve dos máscaras alineadas con el índice del DataFrame original:
    la primera, si la CURP contiene una fecha válida; y la segunda, si la persona
    alcanza la edad mínima en la fecha actual.
    """
    hoy = datetime.now()
    curp_ok_list = []
    edad_ok_list = []

    for curp in df[col_curp]:
        fecha_nac, ok = extraer_fecha_nacimiento_curp(curp)
        if not ok:
            curp_ok_list.append(False)
            edad_ok_list.append(False)
            continue
        
        curp_ok_list.append(True)
        edad = hoy.year - fecha_nac.year - ((hoy.month, hoy.day) < (fecha_nac.month, fecha_nac.day))
        edad_ok_list.append(edad >= edad_minima)

    return pd.Series(curp_ok_list, index=df.index), pd.Series(edad_ok_list, index=df.index)

def validar_tope_ingresos_uma(df: pd.DataFrame, col_ingresos: str = 'ingresos', max_umas: float = 5.0, uma_mensual: float = UMA_MENSUAL_DEFAULT) -> pd.Series:
    """Comprueba que el ingreso sea positivo y no supere el tope de cinco UMAs mensuales."""
    if col_ingresos not in df.columns:
        return pd.Series(False, index=df.index)

    ingresos = pd.to_numeric(df[col_ingresos], errors='coerce').fillna(0.0)
    tope_maximo = max_umas * uma_mensual
    
    return (ingresos > 0) & (ingresos <= tope_maximo)