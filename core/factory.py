from core.readers.aprobaciones import AprobacionesReader
from core.validadores.aprobaciones import AprobacionesValidator

class ProcessFactory:
    _REGISTRO = {
        "APROBACIONES": {
            "reader": AprobacionesReader,
            "validator": AprobacionesValidator
        }
        # Próximamente: "MODIFICACIONES", "CANCELACIONES"
    }

    @classmethod
    def obtener_componentes(cls, tipo_proceso: str):
        key = tipo_proceso.upper().strip()
        if key not in cls._REGISTRO:
            raise ValueError(f"Proceso '{tipo_proceso}' no registrado. Opciones: {list(cls._REGISTRO.keys())}")

        comp = cls._REGISTRO[key]
        return comp["reader"](), comp["validator"]