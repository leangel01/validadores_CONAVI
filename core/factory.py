"""Registro central de los componentes que ejecutan cada tipo de proceso.

Este modulo traduce el nombre de un proceso en el lector y el validador que le
corresponden. Así, la interfaz principal no necesita conocer sus detalles.
"""

from core.readers.aprobaciones import AprobacionesReader
from core.readers.modificaciones import ModificacionesReader
from core.validadores.aprobaciones import AprobacionesValidator
from core.validadores.modificaciones import ModificacionesValidator

class ProcessFactory:
    """Relacion de cada proceso con su lector y su clase validadora."""

    _REGISTRO = {
        "APROBACIONES": {
            "reader": AprobacionesReader,
            "validator": AprobacionesValidator
        },
        "MODIFICACIONES": {
            "reader": ModificacionesReader,
            "validator": ModificacionesValidator
        }
    }

    @classmethod
    def obtener_componentes(cls, tipo_proceso: str):
        """Devuelve una instancia lectora y la clase validadora del proceso.

        Normaliza el nombre recibido para aceptar diferencias de mayúsculas y
        espacios, se rechazan procesos que todavía no estén registrados.
        """
        key = tipo_proceso.upper().strip()
        if key not in cls._REGISTRO:
            raise ValueError(f"Proceso '{tipo_proceso}' no registrado. Opciones: {list(cls._REGISTRO.keys())}")

        comp = cls._REGISTRO[key]
        return comp["reader"](), comp["validator"]