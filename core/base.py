from abc import ABC, abstractmethod
import json
import pandas as pd

class BaseValidator(ABC):
    def __init__(self, ruta_comunes: str, ruta_procesos: str):
        with open(ruta_comunes, 'r', encoding='utf-8') as f:
            self.catalogos_comunes = json.load(f)
        with open(ruta_procesos, 'r', encoding='utf-8') as f:
            self.reglas_procesos = json.load(f)
            
        self.valor_uma = self.catalogos_comunes.get("valor_uma_vigente", 113.14)

    def normalizar_texto(self, valor: str) -> str:
        if pd.isna(valor) or valor is None:
            return ""
        return str(valor).strip().upper()

    @abstractmethod
    def validar_fila(self, row: pd.Series, index: int) -> list:
        """Método abstracto que implementará cada validador específico."""
        pass