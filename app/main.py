from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from app.services import sheets_service, drive_service
from app.services.template import generar_certificado_en_memoria
from datetime import datetime
from collections import defaultdict
from typing import Optional
import re
import locale
from num2words import num2words

# Configurar localización para español
try:
    # Intentar configurar locale español (Linux/Mac)
    locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
except locale.Error:
    try:
        # Fallback para Windows
        locale.setlocale(locale.LC_TIME, 'Spanish_Spain.1252')
    except locale.Error:
        # Si no se puede establecer español, usar C (inglés)
        locale.setlocale(locale.LC_TIME, 'C')


app = FastAPI()
templates = Jinja2Templates(directory="app/templates")

@app.get("/", response_class=HTMLResponse)
def read_root(request: Request):
    """Muestra el formulario para ingresar la cédula."""
    return templates.TemplateResponse("form.html", {"request": request})

@app.post("/verificar-cedula")
def verificar_cedula(cedula: str = Form(...)):
    """
    Endpoint para verificar información preliminar de una cédula.
    Retorna último cargo y estado del contrato.
    """
    # Buscar todos los registros de la cédula
    records = sheets_service.get_records_by_cedula(cedula)
    if not records:
        raise HTTPException(status_code=404, detail=f"No se encontró ningún registro para la cédula {cedula}")
    
    # Ordenar por fecha de ingreso para identificar el contrato más reciente
    # Nota: Asumimos formato de fecha que se puede ordenar lexicográficamente
    sorted_records = sorted(records, key=lambda x: x.get("Fecha de Ingreso", ""), reverse=True)
    latest_record = sorted_records[0]
    
    # Extraer información del contrato más reciente
    ultimo_cargo = latest_record.get("Desc. Cargo", "No especificado")
    fecha_retiro = latest_record.get("Fecha de Retiro", "")
    
    # Determinar si el contrato está activo (Fecha de Retiro vacía)
    contrato_activo = not (fecha_retiro and str(fecha_retiro).strip())
    
    return JSONResponse(content={
        "ultimo_cargo": ultimo_cargo,
        "contrato_activo": contrato_activo
    })

def format_date_str(date_str: str) -> str:
    """
    Convierte una fecha en formato YYYYMMDD a formato legible en español.
    Ejemplo: "20240201" -> "01 de febrero de 2024"
    
    Args:
        date_str: Fecha en formato YYYYMMDD o cadena vacía
        
    Returns:
        Fecha formateada o "la actualidad" si está vacía
    """
    if not date_str or not str(date_str).strip():
        return "la actualidad"
    
    try:
        # Convertir string a datetime
        date_obj = datetime.strptime(str(date_str).strip(), "%Y%m%d")
        
        # Formatear con locale español configurado
        # Usar %d para día, %B para nombre completo del mes, %Y para año
        formatted = date_obj.strftime("%d de %B de %Y")
        
        # Remover ceros iniciales del día
        formatted = formatted.lstrip('0')
        if formatted.startswith('de'):
            formatted = '1' + formatted
            
        return formatted
    except (ValueError, TypeError):
        # Si no se puede parsear, retornar la fecha original
        return str(date_str) if date_str else "la actualidad"

def numero_a_letras(salario_str: str) -> str:
    """
    Convierte un salario en formato de cadena a su representación en letras.
    Ejemplo: "$2,400,000" -> "Dos millones cuatrocientos mil pesos"
    """
    try:
        # Limpiar la cadena de caracteres no numéricos
        numeros_solo = re.sub(r'[^\d]', '', salario_str)
        if not numeros_solo:
            return "Salario no válido"
        
        # Convertir a entero
        valor_numerico = int(numeros_solo)
        
        # Convertir a palabras en español
        texto_numerico = num2words(valor_numerico, lang='es')
        
        # Capitalizar primera letra y agregar "pesos"
        return f"{texto_numerico.capitalize()} pesos"
    except Exception:
        return "Salario no válido"

@app.post("/generar", response_class=HTMLResponse)
def generate_pdf_and_upload(cedula: str = Form(...), salario_manual: Optional[str] = Form(None),tipo_contrato: str = Form(...)):
    """
    Orquesta la generación y subida de múltiples certificados con lógica de negocio avanzada.
    1. Busca TODOS los registros por cédula en Google Sheets.
    2. Agrupa los contratos por empresa canónica.
    3. Genera un PDF por cada empresa con lógica condicional.
    4. Sube cada PDF a Google Drive.
    5. Devuelve enlaces a todos los archivos subidos.
    """
    # 1. Buscar TODOS los registros por cédula en Google Sheets
    records = sheets_service.get_records_by_cedula(cedula)
    if not records:
        raise HTTPException(status_code=404, detail=f"No se encontró ningún registro para la cédula {cedula}")

    # 2. Obtener diccionario de información de empresas para normalización
    company_info_lookup = sheets_service.get_company_info_lookup()

    # 3. Agrupar contratos por nombre canónico de empresa
    contracts_by_canonical_company = defaultdict(list)
    for record in records:
        # Obtener nombre crudo de la empresa desde bd_contratacion
        raw_company_name = record.get("Nombre de empresa", "Empresa No Especificada")
        
        # Buscar información normalizada de la empresa
        company_info = company_info_lookup.get(raw_company_name)
        
        if company_info:
            # Usar el nombre canónico para agrupación
            canonical_name = company_info["canonical_name"]
        else:
            # Fallback: usar el nombre crudo si no se encuentra en el lookup
            canonical_name = raw_company_name
        
        contracts_by_canonical_company[canonical_name].append(record)

    # 4. Generar certificados por empresa (usando nombres canónicos)
    generated_files = []
    now = datetime.now()
    
    for canonical_company_name, contracts in contracts_by_canonical_company.items():
        try:
            # Obtener nombre del empleado (usar el del primer contrato)
            nombre_completo = contracts[0].get("Nombre del empleado", "Desconocido")
            
            # Consolidar períodos de trabajo para esta empresa con cargos
            periodos_empresa = []
            for contract in contracts:
                fecha_ingreso_raw = contract.get("Fecha de Ingreso", "")
                fecha_retiro_raw = contract.get("Fecha de Retiro", "")
                cargo_periodo = contract.get("Desc. Cargo", "No especificado")
                
                # Formatear fechas usando la función helper
                fecha_ingreso_formateada = format_date_str(fecha_ingreso_raw)
                fecha_retiro_formateada = format_date_str(fecha_retiro_raw)
                
                if fecha_retiro_raw and str(fecha_retiro_raw).strip():
                    periodo = f"• Desde el {fecha_ingreso_formateada} hasta el {fecha_retiro_formateada} en el cargo de {cargo_periodo}"
                else:
                    periodo = f"• Desde el {fecha_ingreso_formateada} hasta la actualidad en el cargo de {cargo_periodo}"
                if periodo not in periodos_empresa:
                    periodos_empresa.append(periodo)
                
                          
            # Consolidar en texto único usando <br/> para saltos de línea en Paragraph
            periodo_consolidado = "<br/>".join(periodos_empresa)
            
            # Obtener datos más recientes (del último contrato)
            latest_contract = contracts[-1]
            cargo = latest_contract.get("Desc. Cargo", "No especificado")
            
            # Determinar si el último contrato está activo
            fecha_retiro_ultimo = latest_contract.get("Fecha de Retiro", "")
            contrato_activo = not (fecha_retiro_ultimo and str(fecha_retiro_ultimo).strip())
            
            # Implementar lógica de salario condicional
            salario_final_num = ""
            salario_final_letras = ""
            
            if contrato_activo:
                # Usar salario manual si fue proporcionado, sino usar el del sistema
                salario_a_usar = salario_manual if salario_manual else latest_contract.get("SALARIO BASICO", "")
                
                if salario_a_usar:
                    salario_final_num = salario_a_usar if '$' in str(salario_a_usar) else f"${salario_a_usar}"
                    salario_final_letras = numero_a_letras(salario_final_num)
            
            # Implementar lógica de texto dinámico
            cargos_pae = ["SUPERVISOR PROGRAMA", "MANIPULADORA ALIMENTOS", "COORDINADOR DE PROGRAMA", "MANIPULADORA"]
            
            # La lógica del texto PAE ahora depende solo del cargo, no del estado del contrato
            if cargo in cargos_pae:
                texto_adicional = "en el programa de alimentación escolar PAE."
            else:
                texto_adicional = f"en la {canonical_company_name}."
            
            # Buscar NIT de la empresa usando el nombre canónico
            company_info = company_info_lookup.get(canonical_company_name)
            if company_info:
                nit_empresa = company_info["nit"]
            else:
                # Fallback: buscar por cualquier contrato del grupo
                nit_empresa = "NIT no encontrado"
                for contract in contracts:
                    raw_name = contract.get("Nombre de empresa", "")
                    contract_info = company_info_lookup.get(raw_name)
                    if contract_info:
                        nit_empresa = contract_info["nit"]
                        break
            
            # Detectar si necesita margen superior extra para papel preimpreso
            extra_margin = canonical_company_name == "CORPORACION HACIA UN VALLE SOLIDARIO"
            
            # Preparar datos para la plantilla con nueva lógica de negocio
            datos_plantilla = {
                "nombre": nombre_completo,
                "cedula": cedula,
                "periodos": periodo_consolidado,
                "cargo": cargo,
                "salario_num": salario_final_num,
                "salario_letras": salario_final_letras,
                "texto_adicional": texto_adicional,
                "nombre_empresa": canonical_company_name,
                "nit_empresa": nit_empresa,
                "extra_top_margin": extra_margin,
                "tipo_contrato": tipo_contrato, # Pasamos el valor a la plantilla
                "dias_texto": num2words(now.day, lang='es'),
                "dias_numero": str(now.day),
                "mes": now.strftime("%B"),
                "año": str(now.year)
            }
            
            # Generar PDF en memoria
            pdf_bytes = generar_certificado_en_memoria(datos_plantilla)
            
            # Crear nombre de archivo descriptivo usando nombre canónico
            company_safe = canonical_company_name.replace(' ', '_').replace(',', '').replace('/', '_')
            pdf_filename = f"Certificado_{nombre_completo.replace(' ', '_')}_{company_safe}_{cedula}.pdf"
            
            # Subir a Google Drive
            file_info = drive_service.upload_pdf(pdf_bytes, pdf_filename)
            view_link = file_info.get("webViewLink")
            
            generated_files.append({
                "empresa": canonical_company_name,
                "filename": pdf_filename,
                "link": view_link
            })
            
        except Exception as e:
            # Si hay error con una empresa, continuar con las otras
            generated_files.append({
                "empresa": canonical_company_name,
                "filename": f"Error: {str(e)}",
                "link": None
            })

    # 5. Generar respuesta con todos los enlaces
    if not generated_files:
        raise HTTPException(status_code=500, detail="No se pudo generar ningún certificado")
    
    # Crear lista HTML de archivos generados
    file_list_html = ""
    for file_info in generated_files:
        if file_info["link"]:
            file_list_html += f'<li><strong>{file_info["empresa"]}</strong>: <a href="{file_info["link"]}" target="_blank">{file_info["filename"]}</a></li>'
        else:
            file_list_html += f'<li><strong>{file_info["empresa"]}</strong>: {file_info["filename"]}</li>'
    
    return HTMLResponse(content=f"""
        <html>
            <head><title>Certificados Generados</title></head>
            <body>
                <h1>Certificados generados y subidos con éxito!</h1>
                <p>Se generaron {len([f for f in generated_files if f["link"]])} certificados:</p>
                <ul>
                    {file_list_html}
                </ul>
                <br>
                <a href="/">Generar otros certificados</a>
            </body>
        </html>
    """)