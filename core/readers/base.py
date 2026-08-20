from abc import ABC, abstractmethod
import pandas as pd
import tkinter as tk
from tkinter import filedialog
from typing import Optional

def seleccionar_archivo() -> Optional[str]:
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    return filedialog.askopenfilename(
        title="Selecciona la plantilla Excel",
        filetypes=[("Archivos de Excel", "*.xlsx *.xls *.xlsm")]
    )

class BaseReader(ABC):
    def __init__(self, ruta_comunes: str = "catalogos/reglas_comunes.json"):
        self.ruta_comunes = ruta_comunes

    def _limpiar_texto(self, df: pd.DataFrame) -> pd.DataFrame:
        """Limpia espacios en blanco y estandariza cadenas."""
        for col in df.select_dtypes(include='object').columns:
            df[col] = df[col].astype(str).str.strip()
        return df

    @abstractmethod
    def cargar_y_preparar(self, ruta_excel: str) -> pd.DataFrame:
        """Cada lector abstracto debe definir cómo parsear su layout específico."""
        pass