# rutas/empleados.py

import os
import math
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import Optional, List, Union
from pymongo import MongoClient

# ——— Configuración de MongoDB ———
mongo_uri = os.getenv("MONGO_URI")
if not mongo_uri:
    raise ValueError("La variable de entorno MONGO_URI no está configurada.")

client = MongoClient(mongo_uri)
db = client["integra"]
coleccion_empleados = db["empleados"]

# ——— Modelo Pydantic ———
class Empleado(BaseModel):
    id: Optional[str]
    nombre: Optional[str]
    identificacion: str
    cargo: Optional[str]
    salario: Optional[int]
    fechaIngreso: Optional[str]
    tipoContrato: Optional[str]

    class Config:
        orm_mode = True

# ——— Función de transformación ———
def transformar_empleado(doc: dict) -> Empleado:
    # Nombre completo
    partes = [
        doc.get("primer_nombre"),
        doc.get("segundo_nombre"),
        doc.get("primer_apellido"),
        doc.get("segundo_apellido"),
    ]
    nombre_completo = " ".join(filter(None, partes)) or None

    # Identificación → string y manejamos NaN
    id_val: Union[int, float, str] = doc.get("identificacion", "")
    if isinstance(id_val, (int, float)):
        if isinstance(id_val, float) and math.isnan(id_val):
            identificacion_str = ""
        else:
            identificacion_str = str(int(id_val))
    else:
        identificacion_str = str(id_val)

    # Fecha de ingreso → mantiene cadena o convierte datetime
    fecha_raw = doc.get("fecha_ingreso")
    if fecha_raw is None:
        fecha_ing_str = None
    elif hasattr(fecha_raw, "isoformat"):
        fecha_ing_str = fecha_raw.isoformat()
    else:
        fecha_ing_str = str(fecha_raw)

    return Empleado(
        id=str(doc.get("_id")),
        nombre=nombre_completo,
        identificacion=identificacion_str,
        cargo=doc.get("cargo_laboral"),
        salario=doc.get("salario_mes"),
        fechaIngreso=fecha_ing_str,
        tipoContrato=doc.get("tipo_contrato"),
    )

# ——— APIRouter ———
ruta_empleado = APIRouter(
    prefix="/empleados",
    tags=["Empleados"],
    responses={status.HTTP_404_NOT_FOUND: {"message": "No encontrado"}},
)

@ruta_empleado.get("/", response_model=List[Empleado])
async def getEmpleados():
    cursor = coleccion_empleados.find()
    return [transformar_empleado(doc) for doc in cursor]

@ruta_empleado.get("/buscar", response_model=Empleado)
async def getEmpleadoPorIdentificacion(identificacion: str):
    # Primero intentamos buscar como número, luego como cadena
    doc = (
        coleccion_empleados.find_one({"identificacion": float(identificacion)}) or
        coleccion_empleados.find_one({"identificacion": identificacion})
    )
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Empleado no encontrado"
        )
    return transformar_empleado(doc)
