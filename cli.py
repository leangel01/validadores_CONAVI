from core.readers.aprobaciones import seleccionar_archivo
from core.factory import ProcessFactory
from pathlib import Path

def main():
    print("=== SISTEMA DE VALIDACIÓN (MÓDULO APROBACIONES) ===")
    
    ruta = seleccionar_archivo()
    if not ruta:
        print("No se seleccionó ningún archivo.")
        return

    try:
        # Instanciar mediante la fábrica
        reader, ValidatorClass = ProcessFactory.obtener_componentes("APROBACIONES")
        
        print("Cargando y estructurando plantilla...")
        df_limpio = reader.cargar_y_preparar(ruta, nombre_hoja="APROBACIONES")
        
        print(f"Ejecutando reglas de validación en {len(df_limpio)} registros...")
        validador = ValidatorClass(df_limpio)
        df_resultado = validador.validar()
        df_salida = df_resultado.loc[
            ~df_resultado['es_valido'], ['no.', 'curp', 'observaciones_sistema']
        ].copy()
        df_salida['observaciones_sistema'] = df_salida['observaciones_sistema'].str.findall(
            r'\[ERR:.*?\]'
        )
        df_salida = df_salida.explode('observaciones_sistema', ignore_index=True)

        ruta_salida = Path(ruta).with_name(f"{Path(ruta).stem}_resultado.xlsx")
        df_salida.to_excel(ruta_salida, index=False, sheet_name="APROBACIONES")
        print(f"Resultado guardado en: {ruta_salida}")

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