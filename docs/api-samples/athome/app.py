from flask import Flask, request, jsonify, render_template_string
import mysql.connector

app = Flask(__name__)

DB_CONFIG = dict(host="localhost", user="root", password="", database="tecnofix_athome")


def get_db():
    return mysql.connector.connect(**DB_CONFIG)


HTML = """
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Buscador AtHome MX</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>
    body { background: #f5f6fa; }
    .card-header { background: #1a1a2e; color: #fff; }
    .badge-stock   { background: #198754; }
    .badge-nostock { background: #dc3545; }
    #results-count { font-size:.85rem; color:#6c757d; }
    #spinner { display:none; }
    table { font-size:.9rem; }
    thead th { background:#1a1a2e; color:#fff; position:sticky; top:0; }
    .table-wrapper { max-height:65vh; overflow-y:auto; }
    .sort-btn.active { background:#1a1a2e; color:#fff; border-color:#1a1a2e; }
  </style>
</head>
<body>
<div class="container py-4">
  <div class="card shadow-sm">
    <div class="card-header py-3 d-flex align-items-center gap-2">
      <span class="fs-5 fw-bold">🔍 Buscador AtHome MX</span>
    </div>
    <div class="card-body">

      <!-- Filtros -->
      <div class="row g-3 mb-3">
        <div class="col-12 col-md-5">
          <input id="q" type="text" class="form-control" placeholder="Buscar por nombre o SKU…">
        </div>
        <div class="col-6 col-md-2">
          <input id="precio_min" type="number" class="form-control" placeholder="Precio mín">
        </div>
        <div class="col-6 col-md-2">
          <input id="precio_max" type="number" class="form-control" placeholder="Precio máx">
        </div>
        <div class="col-12 col-md-3 d-flex align-items-center gap-3 flex-wrap">
          <div class="form-check mb-0">
            <input class="form-check-input" type="checkbox" id="solo_stock">
            <label class="form-check-label" for="solo_stock">Solo con stock</label>
          </div>
          <div class="btn-group btn-group-sm" role="group">
            <button class="btn btn-outline-secondary sort-btn" data-orden="asc"  title="Precio ↑">$ ↑</button>
            <button class="btn btn-outline-secondary sort-btn" data-orden="desc" title="Precio ↓">$ ↓</button>
          </div>
        </div>
      </div>

      <!-- Estado -->
      <div class="d-flex align-items-center gap-2 mb-2">
        <span id="results-count">Escribe para buscar…</span>
        <div id="spinner" class="spinner-border spinner-border-sm text-secondary" role="status"></div>
      </div>

      <!-- Tabla -->
      <div class="table-wrapper border rounded">
        <table class="table table-hover table-bordered mb-0">
          <thead>
            <tr>
              <th>SKU</th>
              <th>Nombre</th>
              <th>Precio</th>
              <th>Stock</th>
              <th>Estado</th>
              <th>Link</th>
            </tr>
          </thead>
          <tbody id="tbody"></tbody>
        </table>
      </div>

    </div>
  </div>
</div>

<script>
  let orden = '';
  let timer = null;

  const inputs = ['q','precio_min','precio_max','solo_stock'];
  inputs.forEach(id => document.getElementById(id).addEventListener(id === 'solo_stock' ? 'change' : 'input', () => { clearTimeout(timer); timer = setTimeout(buscar, 350); }));

  document.querySelectorAll('.sort-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const nuevo = btn.dataset.orden;
      if (orden === nuevo) {
        orden = '';
        document.querySelectorAll('.sort-btn').forEach(b => b.classList.remove('active'));
      } else {
        orden = nuevo;
        document.querySelectorAll('.sort-btn').forEach(b => b.classList.toggle('active', b.dataset.orden === nuevo));
      }
      buscar();
    });
  });

  async function buscar() {
    const q          = document.getElementById('q').value.trim();
    const precio_min = document.getElementById('precio_min').value;
    const precio_max = document.getElementById('precio_max').value;
    const solo_stock = document.getElementById('solo_stock').checked ? '1' : '0';

    const params = new URLSearchParams({ q, solo_stock });
    if (precio_min) params.set('precio_min', precio_min);
    if (precio_max) params.set('precio_max', precio_max);
    if (orden)      params.set('orden', orden);

    document.getElementById('spinner').style.display = 'inline-block';

    const res  = await fetch('/api/buscar?' + params);
    const data = await res.json();

    document.getElementById('spinner').style.display = 'none';
    document.getElementById('results-count').textContent = `${data.length} resultado(s)`;

    const tbody = document.getElementById('tbody');
    if (!data.length) {
      tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted py-3">Sin resultados</td></tr>';
      return;
    }

    tbody.innerHTML = data.map(p => {
      const badge = p.disponible
        ? '<span class="badge badge-stock">En stock</span>'
        : '<span class="badge badge-nostock">Agotado</span>';
      const link = p.url
        ? `<a href="${p.url}" target="_blank" class="btn btn-sm btn-outline-secondary py-0">Ver</a>`
        : '—';
      return `<tr>
        <td class="text-nowrap">${p.sku ?? '—'}</td>
        <td>${p.nombre ?? '—'}</td>
        <td class="text-nowrap">$${parseFloat(p.precio).toLocaleString('es-MX', {minimumFractionDigits:2})}</td>
        <td class="text-center">${p.stock ?? 0}</td>
        <td>${badge}</td>
        <td>${link}</td>
      </tr>`;
    }).join('');
  }
</script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(HTML)


@app.route("/api/buscar")
def buscar():
    q          = request.args.get("q", "").strip()
    solo_stock = request.args.get("solo_stock", "0") == "1"
    precio_min = request.args.get("precio_min", type=float)
    precio_max = request.args.get("precio_max", type=float)
    orden      = request.args.get("orden", "asc")

    sql    = "SELECT nombre, sku, precio, stock, disponible, url FROM productos WHERE 1=1"
    params = []

    if q:
        sql += " AND (nombre LIKE %s OR sku LIKE %s)"
        params += [f"%{q}%", f"%{q}%"]

    if solo_stock:
        sql += " AND disponible = 1"

    if precio_min is not None:
        sql += " AND precio >= %s"
        params.append(precio_min)

    if precio_max is not None:
        sql += " AND precio <= %s"
        params.append(precio_max)

    direction = "ASC" if orden == "asc" else "DESC"
    sql += f" ORDER BY precio {direction} LIMIT 300"

    conn = get_db()
    cur  = conn.cursor(dictionary=True)
    cur.execute(sql, params)
    rows = cur.fetchall()
    cur.close()
    conn.close()

    for r in rows:
        r["precio"] = float(r["precio"]) if r["precio"] else 0.0

    return jsonify(rows)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
