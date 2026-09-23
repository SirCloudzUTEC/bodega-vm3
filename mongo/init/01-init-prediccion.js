// Inicializa prediccion_db para el microservicio Predicción (Node.js).
// Corre una sola vez (volumen vacío), autenticado como root de la instancia.
const predictionDb = db.getSiblingDB('prediccion_db');

if (!predictionDb.getCollectionNames().includes('predicciones')) {
  predictionDb.createCollection('predicciones');
}

// Una predicción por producto y día UTC: prediccion-api hace upsert sobre esta clave.
predictionDb.predicciones.createIndex(
  { producto_id: 1, fecha: -1 },
  { unique: true, name: 'idx_producto_fecha' }
);

// Usuario de aplicación 'bodega' con permisos solo sobre prediccion_db.
// La contraseña llega por variable de entorno (MONGO_PASSWORD en .env), nunca escrita aquí.
const appPassword = process.env.MONGO_APP_PASSWORD;
if (!appPassword) throw new Error('MONGO_APP_PASSWORD es obligatorio');
if (predictionDb.getUser('bodega') === null) {
  predictionDb.createUser({
    user: 'bodega',
    pwd: appPassword,
    roles: [{ role: 'readWrite', db: 'prediccion_db' }],
  });
}
