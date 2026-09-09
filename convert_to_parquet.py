import os
import re
from pathlib import Path
import pandas as pd
import numpy as np

def parse_line(line):
    if len(line) < 13:
        return None
    
    id_estacion = line[0:5]
    try:
        anio = int(line[5:9])
        mes = int(line[9:11])
        dia = int(line[11:13])
    except ValueError:
        return None
    
    rest = line[13:]
    tokens = re.findall(r'-?\d+\.?\d*', rest)
    
    if len(tokens) >= 3:
        try:
            tmax = float(tokens[0])
            tmin = float(tokens[1])
            precip = float(tokens[2])
            
            # Limpieza de nulos (-99.9, -99, etc.)
            tmax = tmax if tmax > -90 else np.nan
            tmin = tmin if tmin > -90 else np.nan
            precip = precip if precip >= 0 else np.nan
            
            return {
                "id_estacion": id_estacion,
                "fecha": f"{anio:04d}-{mes:02d}-{dia:02d}",
                "anio": anio,
                "mes": mes,
                "dia": dia,
                "tmax": tmax,
                "tmin": tmin,
                "precip": precip
            }
        except ValueError:
            return None
    return None

def process_dat_files():
    # Obtener el directorio donde está ubicado este archivo .py
    base_dir = Path(__file__).parent.resolve()
    datos_dir = base_dir / "datos_crudos"
    
    # Buscar recursivamente en smn, inta, ema y cualquier subcarpeta
    file_list = []
    if datos_dir.exists():
        for ext in ["*.dat", "*.DAT", "*.txt"]:
            file_list.extend(list(datos_dir.rglob(ext)))
    else:
        # Resguardo: si no existe 'datos_crudos', busca en la carpeta actual
        print(f"⚠️ No se encontró la carpeta 'datos_crudos' en {base_dir}. Buscando en directorio raíz...")
        for ext in ["*.dat", "*.DAT", "*.txt"]:
            file_list.extend(list(base_dir.rglob(ext)))

    print(f"Directorio de trabajo: {base_dir}")
    print(f"Procesando {len(file_list)} archivo(s) en subcarpetas...")
    
    if not file_list:
        print("❌ No se encontraron archivos .dat/.txt para procesar.")
        return

    all_data = []
    for filepath in file_list:
        print(f" -> Leyendo: {filepath.relative_to(base_dir)}")
        with open(filepath, 'r', encoding='latin-1', errors='ignore') as f:
            for line in f:
                parsed = parse_line(line.strip())
                if parsed:
                    all_data.append(parsed)
                    
    if not all_data:
        print("⚠️ No se pudieron extraer registros válidos de los archivos.")
        return

    df = pd.DataFrame(all_data)
    df['fecha'] = pd.to_datetime(df['fecha'])
    
    # Guardar Parquet en la misma carpeta del script
    output_file = base_dir / "estaciones.parquet"
    df.to_parquet(output_file, engine='pyarrow', compression='snappy', index=False)
    print(f"\n✅ ¡Proceso finalizado! Se guardó '{output_file.name}' con {len(df):,} registros.")

if __name__ == "__main__":
    process_dat_files()