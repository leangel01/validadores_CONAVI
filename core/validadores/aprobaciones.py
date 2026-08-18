import pandas as pd
from core.base import BaseValidator

class AprobacionesValidator(BaseValidator):
    
    def validar_especifico(self, df: pd.DataFrame) -> pd.DataFrame:
        """Reglas exclusivas del trámite de Aprobaciones."""
        
        # Ejemplo: Monto aprobado mayor a 0
        if 'monto_aprobado' in df.columns:
            mask_monto = df['monto_aprobado'] > 0
            df.loc[~mask_monto, 'observaciones_sistema'] += '[ERR: Monto aprobado inválido] '

        return df