from core.validators.aprobaciones import AprobacionesValidator
from core.validators.modificaciones import ModificacionesValidator
from core.validators.cancelaciones import CancelacionesValidator

class ValidatorFactory:
    @staticmethod
    def get_validator(tipo_proceso: str, ruta_comunes: str, ruta_procesos: str):
        proceso = tipo_proceso.lower().strip()
        
        if proceso == "aprobaciones":
            return AprobacionesValidator(ruta_comunes, ruta_procesos)
        elif proceso == "modificaciones":
            return ModificacionesValidator(ruta_comunes, ruta_procesos)
        elif proceso == "cancelaciones":
            return CancelacionesValidator(ruta_comunes, ruta_procesos)
        else:
            raise ValueError(f"Tipo de proceso no reconocido: '{tipo_proceso}'")