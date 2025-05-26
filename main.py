import configparser

import pika
import pika.frame
import pika.spec
from atproto import Client,IdResolver,models

config = configparser.ConfigParser()
config.read("config.ini")
uri = pika.URLParameters(config["bsky"]["amqp"])
connection = pika.BlockingConnection(pika.ConnectionParameters(uri.host,uri.port,credentials=uri.credentials,heartbeat=60))
channel = connection.channel()

queue = channel.queue_declare("BSKY-ALERTS",exclusive=True)
channel.queue_bind(queue="BSKY-ALERTS",exchange="feed",routing_key="#")
client = Client()
client.login(config["bsky"]["uname"], config["bsky"]["psswd"])
dm_client = client.with_bsky_chat_proxy()
# create shortcut to convo methods
dm = dm_client.chat.bsky.convo

id_resolver = IdResolver()
# resolve DID
chat_to = id_resolver.handle.resolve('flareproto.bsky.social')

convo = dm.get_convo_for_members(
        models.ChatBskyConvoGetConvoForMembers.Params(members=[chat_to]),
    ).convo

def callback(ch, method:pika.spec.Basic.Deliver, properties:pika.frame.Header, body: bytes):
    
    client.send_post(body.decode())

dm.send_message(
        models.ChatBskyConvoSendMessage.Data(
            convo_id=convo.id,
            message=models.ChatBskyConvoDefs.MessageInput(
                text='ONLINE',
            ),
        )
    )
try:
    channel.basic_consume("BSKY-ALERTS",callback,auto_ack=True)
    channel.start_consuming()
except BaseException as e:
    dm.send_message(
        models.ChatBskyConvoSendMessage.Data(
            convo_id=convo.id,
            message=models.ChatBskyConvoDefs.MessageInput(
                text=f'OFFLINE: {e}',
            ),
        )
    )