import pandas as pd
from pymongo import MongoClient
import tkinter as tk
from tkinter import filedialog, messagebox
import warnings

# Ignorar advertencias de openpyxl
warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")

def show_message(title, message, is_success=True):
    root = tk.Tk()
    root.withdraw()
    if is_success:
        messagebox.showinfo(title, message)
    else:
        messagebox.showerror(title, message)

def upload_empleados():
    try:
        # Conexión a MongoDB Atlas
        client = MongoClient(
            "mongodb+srv://integra:integra2025@integrappi.agvcg.mongodb.net/?retryWrites=true&w=majority&appName=integrappi"
        )
        db = client["integra"]
        collection = db["empleados"]

        # Eliminar documentos existentes
        collection.delete_many({})

        # Pedir al usuario que seleccione el archivo Excel
        root = tk.Tk()
        root.withdraw()
        file_path = filedialog.askopenfilename(
            title="Seleccione el archivo de empleados",
            filetypes=[("Archivos de Excel", "*.xlsx *.xls")]
        )
        if not file_path:
            show_message("Operación cancelada", "No se seleccionó ningún archivo.", is_success=False)
            return

        # Leer Excel
        df = pd.read_excel(file_path)

        # Reemplazar NaN por None
        df = df.where(pd.notnull(df), None)

        # Convertir columnas datetime a ISO format o None
        for col in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                df[col] = df[col].apply(lambda x: x.isoformat() if pd.notnull(x) else None)

        # Convertir a JSON e insertar en MongoDB
        data_json = df.to_dict(orient='records')
        result = collection.insert_many(data_json)

        # Mostrar éxito
        show_message("Éxito", f"Se subieron {len(result.inserted_ids)} empleados a MongoDB.")

    except Exception as e:
        show_message("Error", f"Ocurrió un error: {str(e)}", is_success=False)

if __name__ == "__main__":
    upload_empleados()
