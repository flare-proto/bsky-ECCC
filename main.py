import configparser

import geopandas
import pika
import pika.frame
import pika.spec
from atproto import Client

config = configparser.ConfigParser()
config.read("config.ini")

connection = pika.BlockingConnection(pika.URLParameters(config["bsky"]["amqp"]))
channel = connection.channel()

queue = channel.queue_declare("BSKY-ALERTS",exclusive=True)
channel.queue_bind(queue,"feed","AX.#")

def callback(ch, method:pika.spec.Basic.Deliver, properties:pika.frame.Header, body):
    client = Client()
    client.login(config["bsky"]["uname"], config["bsky"]["psswd"])

    
channel.basic_consume(queue,callback)