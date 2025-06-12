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
channel.queue_bind(queue="BSKY-ALERTS",exchange="feed",routing_key="*.active.*")
client = Client()



client.login(config["bsky"]["uname"], config["bsky"]["psswd"])
dm_client = client.with_bsky_chat_proxy()
# create shortcut to convo methods
dm = dm_client.chat.bsky.convo

id_resolver = IdResolver()
# resolve DID
chat_to = id_resolver.handle.resolve('flare.protogen.club')

convo = dm.get_convo_for_members(
        models.ChatBskyConvoGetConvoForMembers.Params(members=['did:plc:l2wmxye3cluoydbjmqvlyf5v']),
    ).convo

def split_into_blocks(text, max_len=300):
    blocks = []
    current_block = ""
    sentences = text.split('.')

    for i, sentence in enumerate(sentences):
        sentence = sentence.strip()
        if not sentence:
            continue
        # Add the period back unless it's the last empty split
        sentence_with_period = sentence + '.'
        
        if len(current_block) + len(sentence_with_period) <= max_len:
            current_block += sentence_with_period + ' '
        else:
            if current_block:
                blocks.append(current_block.strip())
            current_block = sentence_with_period + ' '

    if current_block:
        blocks.append(current_block.strip())

    return blocks

def SENDIT(block,last,root):
    if last:
        return models.create_strong_ref(
            client.send_post(block,
            reply_to=models.AppBskyFeedPost.ReplyRef(parent=last, root=root),))
    else:
        return models.create_strong_ref(client.send_post(block))

def callback(ch, method:pika.spec.Basic.Deliver, properties:pika.frame.Header, body: bytes):
    print(len(body))
    if len(body) > 300:
        print(body)
        blocks = split_into_blocks(body.decode())
        last = None
        root = None
        for i in blocks:
            last = SENDIT(i,last,root)
            if not root:
                root = last
    else:
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