from confluent_kafka import Consumer, KafkaException


config = {
    'bootstrap.servers': 'localhost:9092',
    'group.id': 'mi-grupo-consumidor',
    'auto.offset.reset': 'earliest'
}


consumer = Consumer(config)


topic = 'mi-topico'
consumer.subscribe([topic])

print(f'Escuchando mensajes en el tópico "{topic}"...')

try:
    while True:
        msg = consumer.poll(1.0)
        if msg is None:
            continue
        if msg.error():
            raise KafkaException(msg.error())
        else:
            print(f'Mensaje recibido: {msg.value().decode("utf-8")}')
except KeyboardInterrupt:
    print('Cerrando el consumidor...')
finally:
    consumer.close()
