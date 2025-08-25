from io import BytesIO
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_LEFT
from reportlab.platypus import BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer

# --- FUNCIÓN DE DIBUJO ESTÁTICO (MINIMALISTA) ---
def draw_static_elements(canvas, doc):
    """
    Dibuja únicamente la numeración de página en cada hoja.
    El encabezado y el pie de página ahora son parte de la 'story'.
    """
    canvas.saveState()
    width, height = LETTER
    
    canvas.setFont("Helvetica", 9)
    page_num = f"Página {doc.page}"
    canvas.drawRightString(width - inch, 0.75 * inch, page_num)
    
    canvas.restoreState()

def generar_certificado_en_memoria(datos: dict) -> BytesIO:
    """
    Genera un certificado PDF de múltiples páginas con maquetación profesional.
    """
    buf = BytesIO()
    
    # El documento se define con márgenes estándar.
    # El desplazamiento condicional se manejará con un Spacer en la story.
    doc = BaseDocTemplate(
        buf, 
        pagesize=LETTER,
        topMargin=inch,
        bottomMargin=inch,
        leftMargin=inch,
        rightMargin=inch
    )
    
    # Asignamos los datos al documento para que onPage pueda usarlos (aunque ya no los necesite)
    doc.datos = datos
    
    # El Frame y la PageTemplate no cambian, pero ahora onPage llama a la función simplificada.
    content_frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id='content')
    page_template = PageTemplate(id='main_template', frames=[content_frame], onPage=draw_static_elements)
    doc.addPageTemplates([page_template])

    # === DEFINICIÓN DE ESTILOS PROFESIONALES ===
    
    styles = getSampleStyleSheet()
    style_body = ParagraphStyle('Body', parent=styles['Normal'], alignment=TA_JUSTIFY, fontSize=11, leading=18, spaceAfter=12)
    style_periods = ParagraphStyle('Periods', parent=style_body, leftIndent=0.3*inch, fontSize=10)
    style_header = ParagraphStyle('Header', parent=styles['Normal'], alignment=TA_CENTER, fontSize=12, spaceAfter=6, fontName='Helvetica-Bold')
    style_signature = ParagraphStyle('Signature', parent=styles['Normal'], fontSize=11, alignment=TA_LEFT, spaceAfter=6, fontName='Helvetica-Bold')
    style_contact = ParagraphStyle('Contact', parent=styles['Normal'], fontSize=10, alignment=TA_LEFT, spaceAfter=3)
    
    # === CAMBIO 1 (Centrar Dirección): Se modifica la alineación de style_address ===
    style_address = ParagraphStyle(
        'Address', 
        parent=styles['Normal'], 
        fontSize=9, 
        alignment=TA_CENTER, # Se cambió de TA_LEFT a TA_CENTER
        spaceAfter=3
    )

    # === CREACIÓN DE LA "HISTORIA" PLATYPUS CON DESPLAZAMIENTO CONDICIONAL ===
    story = []
    
    # Añadir espaciador condicional para papel Membreteado
    if datos.get("extra_top_margin", False):
        story.append(Spacer(1, 1.50 * inch))
    
    # 2. Mover el encabezado de la empresa y el NIT para que sean los PRIMEROS elementos de la historia
    story.append(Paragraph(datos.get("nombre_empresa", "").upper(), ParagraphStyle(name='CompName', parent=style_header, fontSize=16)))
    
    # === CAMBIO 2 (Aumentar Tamaño NIT): Se añade fontSize al estilo del NIT ===
    story.append(Paragraph(datos.get("nit_empresa", ""), ParagraphStyle(
        name='CompNIT', 
        parent=styles['Normal'], 
        alignment=TA_CENTER, 
        spaceAfter=24,
        fontSize=18  # Se añade esta línea para aumentar el tamaño
    )))
    
    # Certificación principal
    story.append(Paragraph("<b>CERTIFICA QUE</b>", style_header))
    story.append(Spacer(1, 18))
    
    # Párrafo principal con información del empleado
    intro_text = (
        f"El(la) Señor(a) <b>{datos['nombre']}</b> identificado(a) con Cédula de "
        f"Ciudadanía No <b>{datos['cedula']}</b> prestó sus servicios para esta empresa "
        f"en los siguientes periodos:"
    )
    story.append(Paragraph(intro_text, style_body))
    
    # Períodos laborales con sangría
    story.append(Paragraph(datos["periodos"], style_periods))
    
    # Texto dinámico basado en lógica de negocio
    if datos.get('texto_adicional'):
        contrato_seleccionado = datos.get('tipo_contrato', 'Obra o Labor')
        texto_dinamico = f"Mediante contrato de <b>{contrato_seleccionado}</b> {datos['texto_adicional']}"
        story.append(Paragraph(texto_dinamico, style_body))
    
    # Información de salario (condicional)
    if datos.get("salario_num"):
        salario_text = (
            f"Con un salario básico mensual de <b>{datos['salario_num']}</b> "
            f"(<b>{datos['salario_letras']}</b>)."
        )
        story.append(Paragraph(salario_text, style_body))
    
    # Párrafo de cierre
    cierre_text = (
        f"Para constancia de lo anterior se firma en Yumbo a los "
        f"{datos['dias_texto']} ({datos['dias_numero']}) días del mes de "
        f"{datos['mes']} de {datos['año']}."
    )
    story.append(Paragraph(cierre_text, style_body))
    story.append(Spacer(1, 18))
    
    # Despedida
    story.append(Paragraph("Cordialmente,", style_body))
    story.append(Spacer(1, 36))  # Espacio antes de la firma

    # === PIE DE PÁGINA (PARTE DE LA STORY) ===
    # Ya no es necesario redefinir los estilos aquí, se usan los definidos arriba.

    # Línea de firma
    story.append(Paragraph("_______________________________", style_signature))
    story.append(Paragraph("<b>LUISA FERNANDA ORTIZ ERAZO</b>", style_signature))
    story.append(Paragraph("Departamento Gestión Humana", style_contact))
    story.append(Paragraph("Celular: 316 421 95 23", style_contact))
    story.append(Paragraph("Yumbo - Valle del Cauca", style_contact))
    story.append(Spacer(1, 12))
    
    # Dirección de la empresa (ahora se usará el estilo centrado 'style_address')
    story.append(Paragraph("Calle 15 # 26-101 BODEGA 34 COMPLEJO INDUSTRIAL Y COMERCIAL CIC 1", style_address))
    story.append(Paragraph("YUMBO-VALLE", style_address))

    # === CONSTRUCCIÓN DEL DOCUMENTO ===
    doc.build(story)

    # Retornar buffer con el PDF completo
    buf.seek(0)
    return buf