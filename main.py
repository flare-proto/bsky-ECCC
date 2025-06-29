import configparser,collections

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

latest = collections.deque(maxlen=50)

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

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        sentence_with_period = sentence + '.'

        if len(sentence_with_period) <= max_len:
            if len(current_block) + len(sentence_with_period) + 1 <= max_len:
                if current_block:
                    current_block += ' ' + sentence_with_period
                else:
                    current_block = sentence_with_period
            else:
                if current_block:
                    blocks.append(current_block)
                current_block = sentence_with_period
        else:
            # Sentence is too long: split by commas
            chunks = sentence.split(',')
            rebuilt = ""
            for i, chunk in enumerate(chunks):
                chunk = chunk.strip()
                if not chunk:
                    continue
                chunk += ',' if i < len(chunks) - 1 else '.'

                if len(rebuilt) + len(chunk) + 1 <= max_len:
                    if rebuilt:
                        rebuilt += ' ' + chunk
                    else:
                        rebuilt = chunk
                else:
                    if rebuilt:
                        blocks.append(rebuilt)
                    rebuilt = chunk
            if rebuilt:
                blocks.append(rebuilt)
            # Reset current block because the oversized sentence was already handled
            if current_block:
                blocks.append(current_block)
                current_block = ""

    if current_block:
        blocks.append(current_block)

    return blocks


def SENDIT(block,last,root):
    if last:
        return models.create_strong_ref(
            client.send_post(block,
            reply_to=models.AppBskyFeedPost.ReplyRef(parent=last, root=root),))
    else:
        return models.create_strong_ref(client.send_post(block))

def callback(ch, method:pika.spec.Basic.Deliver, properties:pika.frame.Header, body: bytes):
    if body in latest:
        return
    latest.append(body)
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
    print("RDY")
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