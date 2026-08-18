import pandas as pd
from datetime import datetime
from typing import Tuple

# Referencia UMA 2026 en México (Diaria: ~$113.14 -> Mensual: ~$3,439.46)
UMA_DIARIA = 113.14
DIAS_MES = 30.4
UMA_MENSUAL_DEFAULT = UMA_DIARIA * DIAS_MES

def extraer_fecha_nacimiento_curp(curp: str) -> Tuple[datetime, bool]:
    """Extrae la fecha de nacimiento a partir de la estructura del CURP."""
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
    """Valida que la CURP no esté duplicada en la plantilla."""
    if col_curp not in df.columns:
        return pd.Series(True, index=df.index)
    
    curps = df[col_curp].astype(str).str.strip().str.upper()
    es_duplicado = curps.duplicated(keep=False) & (curps != '')
    return ~es_duplicado

def validar_mayoria_edad(df: pd.DataFrame, col_curp: str = 'curp', edad_minima: int = 18) -> Tuple[pd.Series, pd.Series]:
    """Retorna (mask_curp_valida, mask_cumple_edad)."""
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
    """Valida que el ingreso mensual sea mayor a 0 y no supere el tope de UMAs."""
    if col_ingresos not in df.columns:
        return pd.Series(False, index=df.index)

    ingresos = pd.to_numeric(df[col_ingresos], errors='coerce').fillna(0.0)
    tope_maximo = max_umas * uma_mensual
    
    return (ingresos > 0) & (ingresos <= tope_maximo)