"""Carga masiva de datos ficticios, UNA sola vez.

Corre como contenedor 'seed' dentro de docker compose, después de que las
tres bases estén healthy. Cada paso comprueba primero si su tabla principal
ya tiene datos: si los tiene, lo salta. Así, repetir `docker compose up`
nunca duplica registros.
"""
import os
import sys

import mysql.connector
import psycopg2
from pymongo import MongoClient

MYSQL = dict(host=os.environ["MYSQL_HOST"], port=3306, user="bodega",
             password=os.environ["MYSQL_PASSWORD"])
PG = dict(host=os.environ["POSTGRES_HOST"], port=5432, user="bodega",
          password=os.environ["POSTGRES_PASSWORD"], dbname="ventas_db")
MINIMO = 20000  # requisito: >= 20 000 registros en al menos 1 tabla de cada base


def contar_mysql(db, tabla):
    conn = mysql.connector.connect(database=db, **MYSQL)
    try:
        cur = conn.cursor()
        cur.execute(f"SELECT COUNT(*) FROM {tabla}")
        return cur.fetchone()[0]
    finally:
        conn.close()


def contar_pg(tabla):
    conn = psycopg2.connect(**PG)
    try:
        cur = conn.cursor()
        cur.execute(f"SELECT COUNT(*) FROM {tabla}")
        return cur.fetchone()[0]
    finally:
        conn.close()


def contar_mongo():
    client = MongoClient(os.environ["MONGO_URI"], serverSelectionTimeoutMS=10000)
    try:
        return client[os.environ.get("MONGO_DB", "prediccion_db")]["predicciones"].count_documents({})
    finally:
        client.close()


def paso(nombre, contar, sembrar, entorno):
    if contar() > 0:
        print(f"== {nombre}: ya tiene datos, se omite (no se duplican registros)", flush=True)
        return
    print(f"== {nombre}: sembrando...", flush=True)
    os.environ.update(entorno)
    sembrar()


def main():
    base_mysql = {"DB_HOST": MYSQL["host"], "DB_PORT": "3306", "DB_USER": "bodega",
                  "DB_PASSWORD": MYSQL["password"]}
    base_pg = {"DB_HOST": PG["host"], "DB_PORT": "5432", "DB_USER": "bodega",
               "DB_PASSWORD": PG["password"], "DB_NAME": "ventas_db"}

    import seed_inventario
    import seed_prediccion
    import seed_proveedores
    import seed_ventas

    paso("1/4 inventario_db (MySQL)", lambda: contar_mysql("inventario_db", "movimientos_inventario"),
         seed_inventario.main, {**base_mysql, "DB_NAME": "inventario_db"})
    paso("2/4 proveedores_db (MySQL)", lambda: contar_mysql("proveedores_db", "tiempos_entrega"),
         seed_proveedores.main, {**base_mysql, "DB_NAME": "proveedores_db"})
    paso("3/4 ventas_db (PostgreSQL)", lambda: contar_pg("ventas_diarias"),
         seed_ventas.main, base_pg)
    paso("4/4 prediccion_db (MongoDB)", contar_mongo, seed_prediccion.main, {})

    conteos = {
        "inventario_db.productos": contar_mysql("inventario_db", "productos"),
        "inventario_db.movimientos_inventario": contar_mysql("inventario_db", "movimientos_inventario"),
        "proveedores_db.proveedores": contar_mysql("proveedores_db", "proveedores"),
        "proveedores_db.tiempos_entrega": contar_mysql("proveedores_db", "tiempos_entrega"),
        "ventas_db.ventas_diarias": contar_pg("ventas_diarias"),
        "ventas_db.pedidos_proveedor": contar_pg("pedidos_proveedor"),
        "prediccion_db.predicciones": contar_mongo(),
    }
    print("\n== Conteos finales ==")
    for tabla, n in conteos.items():
        print(f"{tabla:40s} {n:>8}")

    # Una tabla/colección con >= 20 000 por cada base (MySQL, PostgreSQL, MongoDB).
    grandes = {
        "MySQL": max(conteos["inventario_db.movimientos_inventario"], conteos["proveedores_db.tiempos_entrega"]),
        "PostgreSQL": conteos["ventas_db.ventas_diarias"],
        "MongoDB": conteos["prediccion_db.predicciones"],
    }
    faltan = [motor for motor, n in grandes.items() if n < MINIMO]
    if faltan:
        print(f"\nERROR: sin tabla >= {MINIMO} en: {', '.join(faltan)}")
        sys.exit(1)
    print(f"\nOK: cada base tiene al menos una tabla/colección con >= {MINIMO} registros")


if __name__ == "__main__":
    main()
