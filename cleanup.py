import configparser,pprint,pytz
from datetime import datetime,timedelta

from atproto import Client,IdResolver,models

config = configparser.ConfigParser()
config.read("config.ini")

client = Client()
client.login(config["bsky"]["uname"], config["bsky"]["psswd"])

OneDay = timedelta(days=1.5)

def posts(cursor=None)-> list[models.AppBskyFeedDefs.PostView]:
    found = []
    profile_feed = client.get_author_feed(actor="weather-alerts-ca.bsky.social",limit=100,cursor=cursor)
    for feed_view in profile_feed.feed:
        time = datetime.fromisoformat(feed_view.post.record.created_at)+OneDay
        if datetime.now(tz=pytz.UTC) > time:
            if feed_view.post.like_count ==0 and feed_view.post.quote_count == 0 and feed_view.post.repost_count == 0 and feed_view.post.embed == None:
                print(feed_view.post.record.created_at)
                found.append(feed_view.post)
    if len(profile_feed.feed) == 100:
        found.extend(posts(profile_feed.cursor))
    return found

p = posts()

for post in p:
    print(post.uri)
    client.delete_post(post.uri)