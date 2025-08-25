from typing import Optional, Dict, List
from app.google_clients import get_gspread_client
from app.config import settings

def get_records_by_cedula(cedula: str) -> List[Dict]:
    """Obtiene TODOS los registros de contratos para una cédula específica"""
    gc = get_gspread_client()
    sh = gc.open_by_key(settings.SHEET_ID)
    ws = sh.worksheet("bd_contratacion")
    rows = ws.get_all_records()
    
    matching_records = []
    for row in rows:
        if str(row.get("cedula", "")).strip() == str(cedula).strip():
            matching_records.append(row)
    
    return matching_records

def get_company_info_lookup() -> Dict[str, Dict[str, str]]:
    """
    Crea un diccionario de consulta avanzado para normalización de empresas.
    
    Returns:
        Dict[str, Dict[str, str]]: Diccionario donde cada alias mapea a:
            {
                "canonical_name": "Nombre oficial de la empresa",
                "nit": "NIT de la empresa"
            }
    
    Ejemplo:
        {
            "CORPORACION": {
                "canonical_name": "CORPORACION HACIA UN VALLE SOLIDARIO",
                "nit": "805.029.170-0"
            },
            "CORPORACION HACIA UN VALLE SOLIDARIO": {
                "canonical_name": "CORPORACION HACIA UN VALLE SOLIDARIO", 
                "nit": "805.029.170-0"
            }
        }
    """
    gc = get_gspread_client()
    sh = gc.open_by_key(settings.SHEET_ID)
    ws = sh.worksheet("Empresas")
    rows = ws.get_all_records()
    
    company_info_lookup = {}
    
    for row in rows:
        empresa_field = row.get("Empresa", "")
        nit = row.get("Nit", "")
        
        if empresa_field and nit:
            # Dividir por comas para obtener lista de alias
            aliases = [alias.strip() for alias in empresa_field.split(",")]
            
            if aliases:
                # El primer nombre en la lista es el nombre canónico (oficial)
                canonical_name = aliases[0]
                
                # Crear entrada para cada alias (incluido el canónico)
                for alias in aliases:
                    if alias:  # Solo agregar si no está vacío
                        company_info_lookup[alias] = {
                            "canonical_name": canonical_name,
                            "nit": nit
                        }
    
    return company_info_lookup

