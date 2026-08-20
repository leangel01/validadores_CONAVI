"""
Contiene las utilidades compartidas para los lectores de los distintos layouts, además hace la
limpieza de textos antes de aplicar reglas de validación.
"""

from abc import ABC, abstractmethod
import pandas as pd
import tkinter as tk
from tkinter import filedialog
from typing import Optional

def seleccionar_archivo() -> Optional[str]:
    """Inicializa una ventana para seleccionar el documento y retorna la ruta del archivo elegido por el usuario."""
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    return filedialog.askopenfilename(
        title="Selecciona la plantilla Excel",
        filetypes=[("Archivos de Excel", "*.xlsx *.xls *.xlsm")]
    )

class BaseReader(ABC):
    """Define la interfaz mínima que debe cumplir cada lector."""

    def __init__(self, ruta_comunes: str = "catalogos/reglas_comunes.json"):
        """Inicializa el lector con la ubicación del catálogo de reglas comunes."""
        self.ruta_comunes = ruta_comunes

    def _limpiar_texto(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normaliza el texto para compararlo con el catálogo."""
        for col in df.select_dtypes(include='object').columns:
            df[col] = df[col].astype(str).str.strip()
        return df

    @abstractmethod
    def cargar_y_preparar(self, ruta_excel: str) -> pd.DataFrame:
        """
        Como se implementara la lectura de diversos layouts, se define este método para que cada lector
        concreto pueda definir su layout específico.
        """
        pass