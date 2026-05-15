import json
import glob
import mysql.connector
from pathlib import Path

DB_HOST = "localhost"
DB_USER = "root"
DB_PASS = ""
DB_NAME = "tecnofix_athome"

# Busca los JSON en el directorio padre (TecnoFix/) o en el actual
base = Path(__file__).parent
json_files = sorted(glob.glob(str(base.parent / "catalogo_athome_parte*.json")))
if not json_files:
    json_files = sorted(glob.glob(str(base / "catalogo_athome_parte*.json")))

if not json_files:
    print("No se encontraron archivos catalogo_athome_parte*.json")
    print("Corre primero script.py para generar el catálogo.")
    exit(1)

print(f"Archivos encontrados: {len(json_files)}")

conn = mysql.connector.connect(host=DB_HOST, user=DB_USER, password=DB_PASS)
cur = conn.cursor()

cur.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
cur.execute(f"USE `{DB_NAME}`")

cur.execute("""
    CREATE TABLE IF NOT EXISTS productos (
        id       INT AUTO_INCREMENT PRIMARY KEY,
        nombre   VARCHAR(500),
        sku      VARCHAR(100),
        precio   DECIMAL(10,2),
        stock    INT DEFAULT 0,
        disponible TINYINT(1) DEFAULT 0,
        url      VARCHAR(1000),
        INDEX idx_sku (sku),
        INDEX idx_precio (precio),
        INDEX idx_disponible (disponible)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
""")

cur.execute("TRUNCATE TABLE productos")
conn.commit()

total = 0
for filepath in json_files:
    with open(filepath, encoding="utf-8") as f:
        products = json.load(f)

    if not products:
        continue

    batch = [
        (
            p.get("nombre"),
            p.get("sku"),
            p.get("precio"),
            p.get("stock", 0) or 0,
            1 if p.get("disponible") else 0,
            p.get("url"),
        )
        for p in products
    ]

    cur.executemany(
        "INSERT INTO productos (nombre, sku, precio, stock, disponible, url) VALUES (%s,%s,%s,%s,%s,%s)",
        batch,
    )
    conn.commit()
    total += len(batch)
    print(f"  {Path(filepath).name}: {len(batch)} productos insertados (acumulado: {total})")

cur.close()
conn.close()
print(f"\nListo. {total} productos en la base de datos '{DB_NAME}'.")
