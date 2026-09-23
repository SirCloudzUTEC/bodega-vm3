# Bodega Inteligente — VM3 (bases de datos)

Tres motores en Docker, en subred privada y sin IP pública. Los grupos de seguridad solo aceptan conexiones de Backend A, Backend B y VM4.

| Motor | Puerto | Bases / tablas | Microservicio dueño |
|---|---|---|---|
| MySQL 8 | 3306 | `inventario_db`: `productos` ↔ `movimientos_inventario` (FK `producto_id`) | Inventario |
| | | `proveedores_db`: `proveedores` ↔ `tiempos_entrega` (FK `proveedor_id`) | Proveedores |
| PostgreSQL 16 | 5432 | `ventas_db`: `ventas_diarias` ↔ `pedidos_proveedor` (FK `venta_id`) | Ventas |
| MongoDB 7 | 27017 | `prediccion_db`: colección `predicciones` (índice único `producto_id` + `fecha`) | Predicción |

El contenedor `seed` carga los datos ficticios **una sola vez** y termina. Si se repite `docker compose up`, detecta que ya hay datos y no duplica nada.

| Tabla / colección | Registros |
|---|---|
| `productos` | 1 500 |
| `movimientos_inventario` | 22 000 |
| `proveedores` | 300 |
| `tiempos_entrega` | 21 000 |
| `ventas_diarias` | 21 000 |
| `pedidos_proveedor` | 1 500 (cada uno vinculado a una venta del mismo producto) |
| `predicciones` | 21 000 (14 días × 1 500 productos) |

## Despliegue (hacer ANTES que los backends)

Por **Session Manager**:

```bash
sudo -iu ubuntu
cd /opt/bodega
git clone <URL_DEL_REPO_VM3> vm3        # o: aws s3 cp s3://NOMBRE_BUCKET/deploy/bodega-vm3.zip . && unzip -q bodega-vm3.zip && mv bodega-vm3 vm3
cd vm3

./generar_env.sh             # crea .env con 5 contraseñas aleatorias y muestra las 3 de aplicación
docker compose up -d --build
docker compose logs -f seed  # esperar "OK: cada base tiene al menos una tabla..." (Ctrl+C para salir)
./verificar.sh
```

`generar_env.sh` imprime `MYSQL_PASSWORD`, `POSTGRES_PASSWORD` y `MONGO_PASSWORD`. Esas **tres** líneas van en el `.env` de Backend A, Backend B y VM4. Cópialas por Session Manager, nunca por chat, capturas ni GitHub. Las contraseñas root se quedan solo en VM3.

### Qué debe verse

- `docker compose ps -a`: `mysql`, `postgres` y `mongo` en `running (healthy)`; `seed` en `exited (0)`.
- `./verificar.sh`:
  - los 7 conteos de la tabla de arriba;
  - las 3 FK (una por cada base SQL que la rúbrica exige relacionar);
  - tres líneas `OK` de ≥ 20 000 (MySQL, PostgreSQL y MongoDB).

## Notas importantes

- Los scripts de `mysql/init`, `postgres/init` y `mongo/init` **solo corren con volúmenes vacíos** (primer arranque). Si cambias contraseñas o esquemas después, no se reaplican. Para empezar de cero **se borran todos los datos**: `docker compose down -v`, y luego `docker compose up -d --build`.
- `docker compose down` (sin `-v`) detiene los contenedores y **conserva** los datos.
- El disco de VM3 tiene `DeleteOnTermination: false`: si se borra la pila, el volumen EBS queda y hay que eliminarlo a mano.
- Backups rápidos para la demo, dentro de VM3:
  - `docker compose exec -T mysql sh -c 'mysqldump -uroot -p"$MYSQL_ROOT_PASSWORD" --databases inventario_db proveedores_db' > mysql.sql`
  - `docker compose exec -T postgres pg_dump -U bodega ventas_db > ventas.sql`

## Problemas frecuentes

| Síntoma | Qué revisar |
|---|---|
| `seed` sale con error de conexión | Las bases aún no estaban listas o `.env` cambió después del primer arranque; `docker compose logs mysql` |
| Un backend no conecta (`Access denied`) | La contraseña de su `.env` no es la de VM3 |
| Un backend no conecta (timeout) | Grupo de seguridad de VM3 o IP privada incorrecta |
| `prediccion-api` no autentica en Mongo | El usuario `bodega` se crea solo en el primer arranque con `MONGO_PASSWORD`; si cambiaste la clave después, hay que recrear el volumen de Mongo |

## Cambios respecto al repo original (VM3-CloudComputing)

- Un solo `docker compose up` levanta las bases **y** carga los datos: antes había que instalar dependencias a mano y correr `run_all.sh`.
- La carga es idempotente: no duplica registros si se repite.
- `pedidos_proveedor.venta_id` con FK real a `ventas_diarias`. Antes `ventas_db` no tenía ninguna relación entre sus 2 tablas, y la rúbrica la exige.
- `predicciones`: 21 000 documentos (antes 1 500, por debajo del mínimo de 20 000).
- La contraseña de Mongo del usuario `bodega` se toma del `.env`; antes estaba escrita como `changeme` en el script de inicio.
- Sin contraseñas por defecto: si falta una variable, `docker compose` se detiene e indica cuál.
