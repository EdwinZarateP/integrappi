# rutas/empleados.py

import os
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import Optional, List, Union
from pymongo import MongoClient
from datetime import datetime

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

# ——— Función para mapear y castear todos los campos ———
def transformar_empleado(doc: dict) -> Empleado:
    # Nombre completo
    partes_nombre = [
        doc.get("primer_nombre"),
        doc.get("segundo_nombre"),
        doc.get("primer_apellido"),
        doc.get("segundo_apellido"),
    ]
    nombre_completo = " ".join(filter(None, partes_nombre)) or None

    # Identificación como string
    id_val: Union[int, float, str] = doc.get("identificacion", "")
    if isinstance(id_val, (int, float)):
        identificacion_str = str(int(id_val))
    else:
        identificacion_str = str(id_val)

    # Fecha de ingreso en ISO
    fecha_ing = doc.get("fecha_ingreso")
    if isinstance(fecha_ing, datetime):
        fecha_ing_str = fecha_ing.isoformat()
    else:
        fecha_ing_str = None

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
    responses={status.HTTP_404_NOT_FOUND: {"message": "No encontrado"}}
)

@ruta_empleado.get("/", response_model=List[Empleado])
async def getEmpleados():
    cursor = coleccion_empleados.find()
    return [transformar_empleado(doc) for doc in cursor]

@ruta_empleado.get("/buscar", response_model=Empleado)
async def getEmpleadoPorIdentificacion(identificacion: str):
    # Pymongo convertirá la query si guardaste número o string
    doc = coleccion_empleados.find_one({"identificacion": identificacion})
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Empleado no encontrado"
        )
    return transformar_empleado(doc)
