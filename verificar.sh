#!/usr/bin/env bash
# Estado de VM3: contenedores, conteos por tabla, FK de ventas_db y requisito de >= 20 000.
# Las contraseñas se leen DENTRO de cada contenedor: no quedan en el historial.
cd "$(dirname "$0")"
dc() { docker compose exec -T "$@"; }
echo "== Contenedores"; docker compose ps -a --format 'table {{.Service}}\t{{.State}}\t{{.Status}}'
echo; echo "== Conteos"
my() { dc mysql sh -c "mysql -ubodega -p\"\$MYSQL_PASSWORD\" -N -e 'SELECT COUNT(*) FROM $1' 2>/dev/null"; }
pg() { dc postgres psql -U bodega -d ventas_db -tAc "SELECT COUNT(*) FROM $1"; }
mg() { dc mongo sh -c 'mongosh --quiet -u admin -p "$MONGO_INITDB_ROOT_PASSWORD" --authenticationDatabase admin --eval "db.getSiblingDB(\"prediccion_db\").predicciones.countDocuments({})"'; }
declare -A n
n[inventario_db.productos]=$(my inventario_db.productos)
n[inventario_db.movimientos_inventario]=$(my inventario_db.movimientos_inventario)
n[proveedores_db.proveedores]=$(my proveedores_db.proveedores)
n[proveedores_db.tiempos_entrega]=$(my proveedores_db.tiempos_entrega)
n[ventas_db.ventas_diarias]=$(pg ventas_diarias)
n[ventas_db.pedidos_proveedor]=$(pg pedidos_proveedor)
n[prediccion_db.predicciones]=$(mg)
for t in inventario_db.productos inventario_db.movimientos_inventario proveedores_db.proveedores \
         proveedores_db.tiempos_entrega ventas_db.ventas_diarias ventas_db.pedidos_proveedor prediccion_db.predicciones; do
  printf '%-40s %8s\n' "$t" "${n[$t]:-ERROR}"
done
echo; echo "== Relaciones (FK) por base SQL"
dc mysql sh -c "mysql -ubodega -p\"\$MYSQL_PASSWORD\" -N -e \"SELECT CONCAT(TABLE_SCHEMA,'.',TABLE_NAME,'.',COLUMN_NAME,' -> ',REFERENCED_TABLE_NAME,'.',REFERENCED_COLUMN_NAME) FROM information_schema.KEY_COLUMN_USAGE WHERE REFERENCED_TABLE_NAME IS NOT NULL AND TABLE_SCHEMA IN ('inventario_db','proveedores_db')\" 2>/dev/null"
dc postgres psql -U bodega -d ventas_db -tAc "SELECT conrelid::regclass||' -> '||confrelid::regclass||' ('||conname||')' FROM pg_constraint WHERE contype='f'"
echo; fallo=0
mysql_max=$(( ${n[inventario_db.movimientos_inventario]:-0} > ${n[proveedores_db.tiempos_entrega]:-0} ? ${n[inventario_db.movimientos_inventario]:-0} : ${n[proveedores_db.tiempos_entrega]:-0} ))
for par in "MySQL:$mysql_max" "PostgreSQL:${n[ventas_db.ventas_diarias]:-0}" "MongoDB:${n[prediccion_db.predicciones]:-0}"; do
  motor=${par%%:*}; val=${par#*:}
  if [ "${val:-0}" -ge 20000 ] 2>/dev/null; then echo "OK    $motor tiene una tabla con $val registros (>= 20 000)"; else echo "FALLA $motor: máximo $val (< 20 000)"; fallo=1; fi
done
exit $fallo
