"""Validaciones específicas para aprobaciones del esquema PVB.

Comprueba la alineación de las líneas de apoyo, sus topes en UMAs y la
coincidencia entre la suma de importes y el monto total aprobado.
"""

import json
from pathlib import Path

import pandas as pd

from core.base import BaseValidator


class AprobacionesPVBValidator(BaseValidator):
    """Valida alineación y montos del layout de aprobaciones PVB."""

    def __init__(self, df: pd.DataFrame, config: dict = None):
        """Inicializa el validador con la UMA mensual y el catálogo PVB."""
        super().__init__(df, config)
        ruta_reglas = Path(__file__).resolve().parents[2] / "catalogos" / "reglas_procesos.json"
        with ruta_reglas.open("r", encoding="utf-8") as archivo:
            self.reglas_procesos = json.load(archivo).get("lineas_autorizadas_pvs", {})

    @staticmethod
    def _texto(valor) -> str:
        """Normaliza un nombre de línea y trata el guion como línea no asignada."""
        if pd.isna(valor):
            return ""
        texto = str(valor).strip().upper()
        return "" if texto in ("", "-") else texto

    @staticmethod
    def _numero(valor) -> float:
        """Convierte importes vacíos, inválidos o marcados con guion en cero."""
        if pd.isna(valor) or str(valor).strip() == "-":
            return 0.0
        try:
            return float(valor)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _formatear_monto(valor: float) -> str:
        return f"{valor:,.2f}"

    @staticmethod
    def _supera_tope(valor: float, tope: float) -> bool:
        return round(valor, 2) > round(tope, 2)

    @staticmethod
    def _agregar_error(df: pd.DataFrame, indice, mensaje: str) -> None:
        df.at[indice, "observaciones_sistema"] += f"[ERR: {mensaje}] "

    def _obtener_regla(self, esquema: str, modalidad: str, linea: str):
        return self.reglas_procesos.get(f"{esquema}|{modalidad}|{linea}")

    def _validar_alineacion_principal(
        self,
        df: pd.DataFrame,
        indice,
        esquema: str,
        modalidad: str,
        linea: str,
        numero: int,
    ):
        """Obtiene la regla de una línea principal y reporta alineaciones inválidas."""
        if not linea:
            return None
        regla = self._obtener_regla(esquema, modalidad, linea)
        if regla is None:
            self._agregar_error(
                df,
                indice,
                f"Alineación no encontrada para línea de apoyo {numero}: "
                f'esquema="{esquema or "VACÍO"}", modalidad="{modalidad or "VACÍA"}", '
                f'línea="{linea}"',
            )
        return regla

    def _validar_principal(
        self,
        df: pd.DataFrame,
        indice,
        fila,
        numero: int,
        esquema: str,
        modalidad: str,
        viviendas: float,
    ):
        columna_linea = f"linea_apoyo_{numero}"
        columna_monto = f"monto_linea_apoyo_{numero}"
        linea = self._texto(fila.get(columna_linea, ""))
        monto = self._numero(fila.get(columna_monto, 0))

        if not linea:
            if monto > 0:
                self._agregar_error(
                    df, indice, f"Monto asignado sin línea de apoyo {numero}"
                )
            return None, monto

        regla = self._validar_alineacion_principal(
            df, indice, esquema, modalidad, linea, numero
        )
        if regla is not None:
            tope = regla.get("uma_la", 0) * self.uma_mensual * viviendas
            if self._supera_tope(monto, tope):
                self._agregar_error(
                    df,
                    indice,
                    f"Monto de línea de apoyo {numero} supera el máximo de "
                    f"{self._formatear_monto(tope)} pesos "
                    f'({regla.get("uma_la", 0)} UMAs por vivienda)',
                )
        return regla, monto

    def _validar_complementarias(
        self,
        df: pd.DataFrame,
        indice,
        fila,
        regla,
        linea_principal: str,
        viviendas: float,
    ) -> float:
        """Valida las seis posiciones complementarias de la línea principal 4."""
        suma = 0.0
        complementarias = regla.get("complementarias_permitidas", {}) if regla else {}

        for numero in range(1, 7):
            nombre = self._texto(fila.get(f"linea_complementaria_{numero}", ""))
            monto = self._numero(fila.get(f"monto_linea_complementaria_{numero}", 0))
            suma += monto

            if not nombre:
                if monto > 0:
                    self._agregar_error(
                        df, indice, f"Monto asignado sin línea complementaria {numero}"
                    )
                continue

            if not linea_principal:
                self._agregar_error(
                    df,
                    indice,
                    f"Línea complementaria {numero} asignada sin línea de apoyo 4",
                )
                continue

            if regla is None:
                continue

            uma_lc = complementarias.get(nombre)
            if uma_lc is None:
                self._agregar_error(
                    df, indice, f"Línea complementaria no permitida: {nombre}"
                )
                continue

            tope = uma_lc * self.uma_mensual * viviendas
            if self._supera_tope(monto, tope):
                self._agregar_error(
                    df,
                    indice,
                    f"Monto de {nombre} supera el máximo de "
                    f"{self._formatear_monto(tope)} pesos "
                    f"({uma_lc} UMAs por vivienda)",
                )

        return suma

    def _validar_fila(self, df: pd.DataFrame, indice, fila) -> None:
        esquema = self._texto(fila.get("esquema", ""))
        modalidad = self._texto(fila.get("modalidad", ""))
        viviendas = self._numero(fila.get("total_viviendas", 0))
        montos = 0.0

        for numero in range(1, 4):
            _, monto = self._validar_principal(
                df, indice, fila, numero, esquema, modalidad, viviendas
            )
            montos += monto

        regla_principal_4, monto_principal_4 = self._validar_principal(
            df, indice, fila, 4, esquema, modalidad, viviendas
        )
        montos += monto_principal_4
        linea_principal_4 = self._texto(fila.get("linea_apoyo_4", ""))
        monto_complementarias = self._validar_complementarias(
            df,
            indice,
            fila,
            regla_principal_4,
            linea_principal_4,
            viviendas,
        )
        montos += monto_complementarias

        if regla_principal_4 is not None:
            tope_total = regla_principal_4.get("uma_max", 0) * self.uma_mensual * viviendas
            if self._supera_tope(monto_principal_4 + monto_complementarias, tope_total):
                self._agregar_error(
                    df,
                    indice,
                    "La suma de línea de apoyo 4 y sus complementarias supera el máximo de "
                    f"{self._formatear_monto(tope_total)} pesos "
                    f'({regla_principal_4.get("uma_max", 0)} UMAs por vivienda)',
                )

        monto_aprobado = self._numero(fila.get("total_monto_aprobado", 0))
        if abs(round(montos - monto_aprobado, 2)) > 0.01:
            self._agregar_error(
                df,
                indice,
                f"La suma de todos los montos ({self._formatear_monto(montos)}) "
                f"no coincide con el monto total aprobado "
                f"({self._formatear_monto(monto_aprobado)})",
            )

    def validar_especifico(self, df: pd.DataFrame) -> pd.DataFrame:
        """Ejecuta las validaciones exclusivas de aprobaciones PVB."""
        for indice, fila in df.iterrows():
            self._validar_fila(df, indice, fila)
        return df

    def validar(self) -> pd.DataFrame:
        """Valida el dataframe PVB sin aplicar reglas comunes de S100."""
        df_resultado = self.df.copy()
        df_resultado["observaciones_sistema"] = ""
        df_resultado = self.validar_especifico(df_resultado)
        df_resultado["es_valido"] = df_resultado["observaciones_sistema"] == ""
        return df_resultado