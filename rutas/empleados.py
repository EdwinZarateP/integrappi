# Dependencias necesarias:
# pip install fastapi uvicorn pymongo reportlab resend
import os
import io
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List
from pymongo import MongoClient
import resend
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph
from datetime import datetime

# ——— Configuración de MongoDB ———
mongo_uri = os.getenv("MONGO_URI")
if not mongo_uri:
    raise ValueError("La variable de entorno MONGO_URI no está configurada.")
client = MongoClient(mongo_uri)
db = client["integra"]
coleccion_empleados = db["empleados"]

# ——— Configuración de Resend ———
resend_api_key = os.getenv("RESEND_API_KEY")
if not resend_api_key:
    raise ValueError("La variable de entorno RESEND_API_KEY no está configurada.")
resend.api_key = resend_api_key  # configure el SDK

# ——— Modelos Pydantic ———
class Empleado(BaseModel):
    id: Optional[str]
    identificacion: str
    nombre: Optional[str]
    cargo: Optional[str]
    tipoContrato: Optional[str]
    fechaIngreso: Optional[str]
    basico: Optional[float]
    auxilioVivienda: Optional[float]
    auxilioAlimentacion: Optional[float]
    auxilioMovilidad: Optional[float]
    auxilioRodamiento: Optional[float]
    auxilioProductividad: Optional[float]
    auxilioComunic: Optional[float]
    correo: Optional[str]

    class Config:
        orm_mode = True

class EnviarRequest(BaseModel):
    incluirSalario: bool

# ——— Función de transformación ———
def transformar_empleado(doc: dict) -> Empleado:
    get = lambda *keys: next((doc.get(k) for k in keys if k in doc), None)
    def get_float(*keys):
        try:
            return float(get(*keys) or 0)
        except:
            return 0

    fecha_raw = get('fechaIngreso','FECHA_INGRESO','FECHA INGRESO')
    fecha_ing = fecha_raw.isoformat() if hasattr(fecha_raw, 'isoformat') else str(fecha_raw or '')

    return Empleado(
        id=str(doc.get('_id')),
        identificacion=str(get('identificacion','IDENTIFICACIÓN') or ""),
        nombre=get('nombre','NOMBRE'),
        cargo=get('cargo','CARGO'),
        tipoContrato=get('tipoContrato','TIPO_DE_CONTRATO','TIPO DE CONTRATO'),
        fechaIngreso=fecha_ing,
        basico=get_float('basico','BASICO'),
        auxilioVivienda=get_float('auxilioVivienda','AUXILIO_VIVIENDA'),
        auxilioAlimentacion=get_float('auxilioAlimentacion','AUXILIO_ALIMENTA'),
        auxilioMovilidad=get_float('auxilioMovilidad','AUXILIO_DE_MOVILIDAD'),
        auxilioRodamiento=get_float('auxilioRodamiento','AUXILIO_RODAMIENTO'),
        auxilioProductividad=get_float('auxilioProductividad','AUXILIO_DE_PRODUCTIVIDAD'),
        auxilioComunic=get_float('auxilioComunic','AUXILIO_COMUNIC'),
        correo=get('correo','CORREO')
    )

# ——— Router de empleados ———
ruta_empleado = APIRouter(
    prefix="/empleados",
    tags=["Empleados"],
    responses={status.HTTP_404_NOT_FOUND:{"message":"No encontrado"}}
)

@ruta_empleado.get("/", response_model=List[Empleado])
async def get_empleados():
    docs = coleccion_empleados.find()
    return [transformar_empleado(doc) for doc in docs]

@ruta_empleado.get("/buscar", response_model=Empleado)
async def get_empleado_por_identificacion(identificacion: str):
    doc = coleccion_empleados.find_one({"identificacion": identificacion})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empleado no encontrado")
    return transformar_empleado(doc)

@ruta_empleado.post("/enviar")
async def enviar_certificado(identificacion: str, req: EnviarRequest):
    # 1) Buscamos empleado
    doc = coleccion_empleados.find_one({"identificacion": identificacion})
    if not doc:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    emp = transformar_empleado(doc)
    if not emp.correo:
        raise HTTPException(status_code=400, detail="Empleado no tiene correo registrado")

    # 2) Generar PDF en memoria
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # Dibujar fondo (asegúrate de tener 'assets/fondo.png')
    fondo_path = os.path.join(os.getcwd(), 'assets', 'fondo.png')
    c.drawImage(ImageReader(fondo_path), 0, 0, width=width, height=height)

    y = height - 80
    c.setFont("Times-Bold", 14)
    c.drawCentredString(width/2, y, "EL DEPARTAMENTO DE GESTIÓN HUMANA")

    y -= 30
    c.setFont("Times-Roman", 12)
    c.drawCentredString(width/2, y, "CERTIFICA QUE:")

    y -= 30
    fecha_emision = datetime.today().strftime("%d de %B de %Y")
    fecha_ing = emp.fechaIngreso or ""

    text = (f"El señor/a {emp.nombre}, identificado/a con cédula número {emp.identificacion}, "
            f"labora en nuestra empresa desde {fecha_ing}, desempeñando el cargo de {emp.cargo} "
            f"con contrato a término {emp.tipoContrato}.")
    if req.incluirSalario and emp.basico:
        text += f" Con un salario fijo mensual por valor de {int(emp.basico):,} pesos m/cte."

    style = ParagraphStyle('body', fontName='Times-Roman', fontSize=12, leading=14)
    p = Paragraph(text, style)
    p.wrapOn(c, width-40, height)
    p.drawOn(c, 20, y)
    y -= p.height + 20

    # Auxilios
    if req.incluirSalario:
        for label, val in [
            ("Auxilio Vivienda", emp.auxilioVivienda),
            ("Auxilio Alimentación", emp.auxilioAlimentacion),
            ("Auxilio Movilidad", emp.auxilioMovilidad),
            ("Auxilio Rodamiento", emp.auxilioRodamiento),
            ("Auxilio Productividad", emp.auxilioProductividad),
            ("Auxilio Comunic", emp.auxilioComunic)
        ]:
            if val and val > 0:
                c.setFont("Times-Bold", 12)
                c.drawString(20, y, f"{label}: {int(val):,}")
                y -= 18

    # Pie de página y firma
    c.setFont("Times-Roman", 10)
    c.drawString(20, 40, "Para mayor información: PBX 7006232 o celular 3183385709.")
    firma_path = os.path.join(os.getcwd(), 'assets', 'firma.png')
    c.drawImage(ImageReader(firma_path), width/2-75, 60, width=150, height=50)
    c.setFont("Times-Bold", 12)
    c.drawCentredString(width/2, 50, "PATRICIA LEAL AROCA")
    c.setFont("Times-Roman", 10)
    c.drawCentredString(width/2, 35, "Gerente de gestión humana | Integra cadena de servicios")

    c.showPage()
    c.save()
    buffer.seek(0)

    # 3) Enviar correo vía Resend SDK en Python
    params = {
        "from": "no-reply@send.integralogistica.com",
        "to": [emp.correo],
        "subject": f"Certificado Laboral - {emp.nombre}",
        "html": f"<p>Hola {emp.nombre},</p><p>Adjunto tu certificado laboral.</p>",
        "attachments": [
            {
                "filename": f"certificado_{emp.identificacion}.pdf",
                "type": "application/pdf",
                "content": buffer.read()
            }
        ]
    }
    try:
        email = resend.Emails.send(params)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error enviando correo: {e}")

    return JSONResponse(status_code=200, content={"message": "Correo enviado correctamente"})
