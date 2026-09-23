"""Carga ficticia inicial de 21 000 documentos, reproducible por producto y día.
Se ejecuta UNA vez para la demo. El API calcula después predicciones reales.
"""
import random
from datetime import datetime, timedelta, timezone

from pymongo import MongoClient, UpdateOne
from common import MONGO_URI, MONGO_DB_NAME, PRODUCTO_ID_RANGE


def main():
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=10000)
    collection = client[MONGO_DB_NAME]['predicciones']
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    batch = []
    for days_ago in range(14):
        when = today - timedelta(days=days_ago)
        for product_id in PRODUCTO_ID_RANGE:
            rng = random.Random(product_id * 100 + days_ago)
            speed = round(rng.uniform(0.5, 25.0), 2)
            stock = rng.randint(0, 300)
            supply = rng.randint(2, 12)
            days = round(stock / speed, 1)
            risk = max(0.0, min(1.0, 1.0 - (days / supply - 1.0)))
            risk = round(risk, 3)
            doc = {
                'producto_id': product_id, 'fecha': when,
                'velocidad_venta_diaria': speed, 'stock_actual': stock,
                'dias_hasta_agotamiento': days,
                'tiempo_entrega_promedio': supply, 'prob_quiebre': risk,
                'nivel_riesgo': 'alto' if risk > 0.66 else 'medio' if risk > 0.33 else 'bajo',
                'created_at': when,
            }
            batch.append(UpdateOne({'producto_id': product_id, 'fecha': when}, {'$set': doc}, upsert=True))
            if len(batch) == 1000:
                collection.bulk_write(batch, ordered=False)
                batch.clear()
    if batch:
        collection.bulk_write(batch, ordered=False)
    print('Predicciones en Mongo:', collection.count_documents({}))
    client.close()


if __name__ == '__main__':
    main()
