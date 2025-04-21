# rutas/empleados.py

import os
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import Optional, List
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

# ——— Función para mapear y castear todos los campos ———
def transformar_empleado(doc: dict) -> Empleado:
    return Empleado(
        id=str(doc.get("_id")),
        nombre=doc.get("nombre"),
        identificacion=str(doc.get("identificacion", "")),  # ← fuerza a string
        cargo=doc.get("cargo"),
        salario=doc.get("salario"),
        fechaIngreso=doc.get("fechaIngreso"),
        tipoContrato=doc.get("tipoContrato"),
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
    # buscás con string, pero si en Mongo está guardado como número, pymongo hace la conversión interna
    doc = coleccion_empleados.find_one({"identificacion": identificacion})
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Empleado no encontrado"
        )
    return transformar_empleado(doc)
