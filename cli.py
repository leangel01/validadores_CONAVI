"""Módulo principal para ejecutar la validación de los archivos.

El flujo de ejecuciín es:
    - Se pide el archivo,
    - Se leen los datos,
    - Se ejecutan las reglas de validación,
    -Se exportan los errores en un documento de excel y,
    - Se muestra un resumen en la consola.

    
Actulmente, solo se soporta el proceso de APROBACIONES, quedando pendiente la incorporación de validaciones para MODIFICACIONES.


- Respecto a la validación de los ingresos con valores iguales a cero no se tomarán como error, ya que 'en las ROPs no se establece que estos deben de 
  ser superiores a algún monto en específico'.
  Adicionalmente, se incorporan las lineas complementarias que no cuentan con un tope de monto, estas unicamente se validarán en cuanto a la
  alineacion que deben de tener, porque al igual que pasa con la edad, las ROPs no establecen los montos maximos para estos casos.
- En cuanto a la validacion de las MODIFICACIONES, solo se realzarán sobre los montos tope, se validadran tanto los montos anteriores
  como los nuevos. en caso de modificaciones de benficiarios localidad etc. esos no se validarán.
"""

from core.readers.aprobaciones import seleccionar_archivo
from core.factory import ProcessFactory
from pathlib import Path
import pandas as pd

def main():

    opciones = {'1': 'APROBACIONES S100', '2': 'MODIFICACIONES S100'}
    print("=== MÓDULO DE VALIDACIONES ===")
    print("1. Aprobaciones S100")
    print("2. Modificaciones S100")
    tipo_proceso = opciones.get(input("Selecciona el tipo de validación [1/2]: ").strip())
    if tipo_proceso is None:
        print("Opción no válida.")
        return
    print(f"=== VALIDACIÓN DE {tipo_proceso} ===")
    
    ruta = seleccionar_archivo()
    if not ruta:
        print("No se seleccionó ningún archivo.")
        return

    try:

        reader, ValidatorClass = ProcessFactory.obtener_componentes(tipo_proceso)

        print("Cargando y estructurando plantilla...")
        df_limpio = reader.cargar_y_preparar(ruta, nombre_hoja=tipo_proceso)

        print(f"Ejecutando reglas de validación en {len(df_limpio)} registros...")
        validador = ValidatorClass(df_limpio)
        df_resultado = validador.validar()
        # Se seleccionan solo los registros inválidos y las columnas útiles para revisarlos.
        columnas_salida = ['no.', 'curp', 'observaciones_sistema']
        df_salida = df_resultado.loc[~df_resultado['es_valido'], columnas_salida].copy()
        df_salida['observaciones_sistema'] = df_salida['observaciones_sistema'].str.findall(
            r'\[ERR:.*?\]'
        )
        df_salida = df_salida.explode('observaciones_sistema', ignore_index=True)

        ruta_salida = Path(ruta).with_name(f"{Path(ruta).stem}_resultado.xlsx")
        df_homologacion = getattr(
            reader,
            'reporte_homologacion',
            pd.DataFrame(
                columns=['columna', 'original', 'homologado', 'cantidad_ajustes']
            ),
        )
        with pd.ExcelWriter(ruta_salida) as escritor:
            df_salida.to_excel(escritor, index=False, sheet_name=tipo_proceso)
            df_homologacion.to_excel(escritor, index=False, sheet_name='homologación')
        print(f"Resultado guardado en: {ruta_salida}")

        # Muestra un resumen para que el usuario conozca el resultado sin abrir el Excel.
        print("\n--- RESUMEN DE PROCESAMIENTO ---")
        print(f"Total registros: {len(df_resultado)}")
        print(f"VÁLIDOS: {df_resultado['es_valido'].sum()}")
        print(f"CON ERRORES: {(~df_resultado['es_valido']).sum()}")

        df_errores = df_resultado[~df_resultado['es_valido']]
        if not df_errores.empty:
            print("\nPrimeros registros con errores:")
            print(df_errores[['curp', 'observaciones_sistema']].head())

    except Exception as e:
        print(f"\n[Error durante el proceso]: {e}")

if __name__ == "__main__":
    main()