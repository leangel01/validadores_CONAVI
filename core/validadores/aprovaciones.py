from core.base import BaseValidator
import pandas as pd

class AprobacionesValidator(BaseValidator):
    def validar_fila(self, row: pd.Series, index: int) -> list:
        errores = []
        fila_excel = index + 2

        esq = self.normalizar_texto(row.get('esquema'))
        mod = self.normalizar_texto(row.get('modalidad'))
        la = self.normalizar_texto(row.get('linea_de_apoyo'))
        lc = self.normalizar_texto(row.get('linea_complementaria'))

        monto_la = float(row.get('monto_la', 0) or 0)
        monto_lc = float(row.get('monto_lc', 0) or 0)

        # Clave compuesta para búsqueda O(1)
        clave_jerarquia = f"{esq}|{mod}|{la}"
        matriz_reglas = self.reglas_procesos.get("lineas_autorizadas_pvs", {})

        # Validación 1: Existencia de Jerarquía Principal
        if clave_jerarquia not in matriz_reglas:
            errores.append({
                "fila": fila_excel,
                "columna": "linea_de_apoyo",
                "mensaje": f"Combinación no permitida: Esquema '{esq}' | Modalidad '{mod}' | Línea '{la}'."
            })
            return errores

        regla_nodo = matriz_reglas[clave_jerarquia]

        # Validación 2: Tope Monto Línea Principal
        if monto_la > 0:
            tope_la = regla_nodo["uma_la"] * self.valor_uma
            if monto_la > tope_la:
                errores.append({
                    "fila": fila_excel,
                    "columna": "monto_la",
                    "mensaje": f"Monto ${monto_la:,.2f} excede el tope de {regla_nodo['uma_la']} UMA (${tope_la:,.2f})."
                })

        # Validación 3: Línea Complementaria y Tope
        complementarias = regla_nodo["complementarias_permitidas"]
        if lc:
            if lc not in complementarias:
                errores.append({
                    "fila": fila_excel,
                    "columna": "linea_complementaria",
                    "mensaje": f"Línea complementaria '{lc}' no está autorizada para '{la}'."
                })
            elif monto_lc > 0:
                uma_lc_max = complementarias[lc]
                tope_lc = uma_lc_max * self.valor_uma
                if monto_lc > tope_lc:
                    errores.append({
                        "fila": fila_excel,
                        "columna": "monto_lc",
                        "mensaje": f"Monto complementario ${monto_lc:,.2f} excede el tope de {uma_lc_max} UMA (${tope_lc:,.2f})."
                    })

        return errores