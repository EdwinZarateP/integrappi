from fastapi import APIRouter, UploadFile, HTTPException, status, Form
from fastapi.responses import JSONResponse
from pymongo import MongoClient
from google.cloud import storage
from uuid import uuid4
from io import BytesIO
from PIL import Image
import os
from typing import List

# Configuración de MongoDB
mongo_uri = os.getenv("MONGO_URI")
if not mongo_uri:
    raise ValueError("La variable de entorno MONGO_URI no está configurada.")
bd_cliente = MongoClient(mongo_uri)
bd = bd_cliente['integra']
coleccion_vehiculos = bd['vehiculos']

# Configuración de Google Cloud Storage
BUCKET_NAME = "integrapp"
CARPETA_STORAGE = "Vehiculos"

google_credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
if not google_credentials_path:
    raise ValueError("La variable de entorno GOOGLE_APPLICATION_CREDENTIALS no está configurada.")
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = google_credentials_path

# APIRouter para la ruta
ruta_vehiculos = APIRouter(
    prefix="/vehiculos",
    tags=['Vehiculos'],
    responses={status.HTTP_404_NOT_FOUND: {"message": "No encontrado"}}
)

def optimizar_imagen(archivo: UploadFile, formato: str = "WEBP", max_width: int = 1200, max_height: int = 800) -> BytesIO:
    try:
        imagen = Image.open(archivo.file)
        imagen.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
        buffer = BytesIO()
        imagen.save(buffer, format=formato, optimize=True, quality=75)
        buffer.seek(0)
        return buffer
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al optimizar la imagen: {str(e)}")

def subir_a_google_storage(archivo: UploadFile, nombre_archivo: str) -> str:
    try:
        cliente = storage.Client()
        bucket = cliente.bucket(BUCKET_NAME)
        ruta_archivo = f"{CARPETA_STORAGE}/{nombre_archivo}"

        if archivo.content_type.startswith("image/"):
            archivo_optimizado = optimizar_imagen(archivo)
            blob = bucket.blob(ruta_archivo)
            blob.upload_from_file(archivo_optimizado, content_type="image/webp")
        else:
            blob = bucket.blob(ruta_archivo)
            blob.upload_from_file(archivo.file, content_type="application/pdf")

        return f"https://storage.googleapis.com/{BUCKET_NAME}/{ruta_archivo}"
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al subir el archivo a Google Storage: {str(e)}")

def eliminar_de_google_storage(url: str):
    try:
        cliente = storage.Client()
        bucket = cliente.bucket(BUCKET_NAME)
        nombre_archivo = url.split(f"https://storage.googleapis.com/{BUCKET_NAME}/")[-1]
        blob = bucket.blob(nombre_archivo)
        blob.delete()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al eliminar el archivo: {str(e)}")

# Crear vehiculo
@ruta_vehiculos.post("/crear")
async def crear_vehiculo(id_usuario: str = Form(...), placa: str = Form(...)):
    if coleccion_vehiculos.find_one({"placa": placa}):
        raise HTTPException(status_code=400, detail="La placa ya está registrada.")
    
    nuevo_vehiculo = {
        "idUsuario": id_usuario,
        "placa": placa,
        "fotos": [],
        "tarjetaPropiedad": None,
        "soat": None,
        "revisionTecnomecanica": None,
        "tarjetaRemolque": None,
        "polizaResponsabilidad": None,
        "documentoIdentidadConductor": None,
        "condFoto": None,
        "licencia": None,
        "planillaEpsArl": None,
        "documentoIdentidadTenedor": None,
        "condCertificacionBancaria": None,
        "propCertificacionBancaria": None,
        "tenedCertificacionBancaria": None,
        "documentoAcreditacionTenedor": None,
        "rutTenedor": None,
        "documentoIdentidadPropietario": None,
        "rutPropietario": None,

        "condPrimerApellido": None,
        "condSegundoApellido": None,
        "condNombres": None,
        "condCedulaCiudadania": None,
        "condExpedidaEn": None,
        "condDireccion": None,
        "condCiudad": None,
        "condCelular": None,
        "condCorreo": None,
        "condEps": None,
        "condArl": None,
        "condNoLicencia": None,
        "condFechaVencimientoLic": None,
        "condCategoriaLic": None,
        "condGrupoSanguineo": None,
        "condNombreEmergencia": None,
        "condCelularEmergencia": None,
        "condParentescoEmergencia": None,
        "condEmpresaRef": None,
        "condCelularRef": None,
        "condCiudadRef": None,
        "condNroViajesRef": None,
        "condAntiguedadRef": None,
        "condMercTransportada": None,

        "propNombre": None,
        "propDocumento": None,
        "propCiudadExpDoc": None,
        "propCorreo": None,
        "propCelular": None,
        "propDireccion": None,
        "propCiudad": None,

        "tenedNombre": None,
        "tenedDocumento": None,
        "tenedCiudadExpDoc": None,
        "tenedCorreo": None,
        "tenedDireccion": None,
        "tenedCiudad": None,        
        "tenedCelular": None,

        "vehModelo": None,
        "vehMarca": None,
        "vehTipoCarroceria": None,
        "vehLinea": None,
        "vehColor": None,
        "vehRepotenciado": None,
        "vehAno": None,
        "vehEmpresaSat": None,
        "vehUsuarioSat": None,
        "vehClaveSat": None,

        "RemolPlaca": None,
        "RemolModelo": None,
        "RemolClase": None,
        "RemolTipoCarroceria": None,
        "RemolAlto": None,
        "RemolLargo": None,
        "RemolAncho": None,
    }
    coleccion_vehiculos.insert_one(nuevo_vehiculo)
    return JSONResponse(status_code=status.HTTP_201_CREATED, content={"message": "Vehículo registrado exitosamente"})


@ruta_vehiculos.put("/subir-documento")
async def subir_documento(archivo: UploadFile, placa: str = Form(...), tipo: str = Form(...)):
    # Validamos si el tipo de documento es de los permitidos
    if tipo not in [
    "tarjetaPropiedad", "soat", "revisionTecnomecanica",  "tarjetaRemolque","polizaResponsabilidad", 
    "documentoIdentidadConductor", "documentoIdentidadPropietario", "documentoIdentidadTenedor", 
    "licencia", "planillaEpsArl", "condFoto", "condCertificacionBancaria", "propCertificacionBancaria", 
    "tenedCertificacionBancaria", "documentoAcreditacionTenedor", "rutTenedor", "rutPropietario"
]:

        raise HTTPException(status_code=400, detail="Tipo de documento no válido.")

    # Buscamos el vehículo
    vehiculo = coleccion_vehiculos.find_one({"placa": placa})
    if not vehiculo:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado.")

    # Definimos la extensión según el tipo de contenido
    if archivo.content_type.startswith("image/"):
        extension = "webp"
    elif archivo.content_type == "application/pdf":
        extension = "pdf"
    else:
        raise HTTPException(
            status_code=400,
            detail="Solo se permiten archivos de imagen o PDF."
        )

    # Construimos el nombre de archivo apropiado
    nombre_archivo = f"{tipo}_{placa}.{extension}"

    # Subimos a Google Storage (la función ya maneja la compresión si es imagen)
    url_archivo = subir_a_google_storage(archivo, nombre_archivo)

    # Guardamos la URL en MongoDB
    coleccion_vehiculos.update_one({"placa": placa}, {"$set": {tipo: url_archivo}})

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": f"{tipo} subido correctamente",
            "url": url_archivo
        }
    )

@ruta_vehiculos.put("/subir-fotos")
async def subir_fotos(archivos: List[UploadFile], placa: str = Form(...)):
    vehiculo = coleccion_vehiculos.find_one({"placa": placa})
    if not vehiculo:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado.")

    urls_fotos = []
    for archivo in archivos:
        nombre_archivo = f"Foto_{placa}_{uuid4().hex}.webp"
        url_archivo = subir_a_google_storage(archivo, nombre_archivo)
        urls_fotos.append(url_archivo)

    coleccion_vehiculos.update_one({"placa": placa}, {"$push": {"fotos": {"$each": urls_fotos}}})
    return JSONResponse(status_code=status.HTTP_200_OK, content={"message": "Fotos subidas correctamente", "urls": urls_fotos})

@ruta_vehiculos.delete("/eliminar-documento")
async def eliminar_documento(placa: str, tipo: str):
    vehiculo = coleccion_vehiculos.find_one({"placa": placa})
    if not vehiculo or not vehiculo.get(tipo):
        raise HTTPException(status_code=404, detail="Documento no encontrado.")
    eliminar_de_google_storage(vehiculo[tipo])
    coleccion_vehiculos.update_one({"placa": placa}, {"$set": {tipo: None}})
    return JSONResponse(status_code=status.HTTP_200_OK, content={"message": f"{tipo} eliminado correctamente"})

@ruta_vehiculos.delete("/eliminar-foto")
async def eliminar_foto(placa: str, url: str):
    vehiculo = coleccion_vehiculos.find_one({"placa": placa})
    if not vehiculo or url not in vehiculo["fotos"]:
        raise HTTPException(status_code=404, detail="Foto no encontrada.")
    eliminar_de_google_storage(url)
    coleccion_vehiculos.update_one({"placa": placa}, {"$pull": {"fotos": url}})
    return JSONResponse(status_code=status.HTTP_200_OK, content={"message": "Foto eliminada correctamente"})

@ruta_vehiculos.get("/obtener-vehiculo/{placa}")
async def obtener_vehiculo(placa: str):
    vehiculo = coleccion_vehiculos.find_one({"placa": placa}, {"_id": 0})
    if not vehiculo:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado.")
    return JSONResponse(status_code=status.HTTP_200_OK, content={"message": "Vehículo encontrado", "data": vehiculo})

@ruta_vehiculos.get("/obtener-vehiculos")
def obtener_vehiculos(id_usuario: str):

    vehiculos = list(coleccion_vehiculos.find({"idUsuario": id_usuario}, {"_id": 0, "placa": 1}))
    if not vehiculos:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"message": "No se encontraron vehículos para este usuario."})
    return JSONResponse(status_code=status.HTTP_200_OK, content={"message": "Vehículos encontrados", "vehicles": vehiculos})


# Actualiza la informacion de datos
@ruta_vehiculos.put("/actualizar-informacion/{placa}")
async def actualizar_informacion_vehiculo(placa: str, datos: dict):
    # Verificar si el vehículo existe
    vehiculo = coleccion_vehiculos.find_one({"placa": placa})
    if not vehiculo:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado.")

    # Actualizar la información en la base de datos
    resultado = coleccion_vehiculos.update_one({"placa": placa}, {"$set": datos})

    if resultado.modified_count == 0:
        return JSONResponse(status_code=200, content={"message": "No se realizaron cambios en el vehículo."})
    
    return JSONResponse(status_code=200, content={"message": "Información del vehículo actualizada exitosamente"})
