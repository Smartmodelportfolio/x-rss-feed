from fastapi import FastAPI
from fastapi.responses import Response
from twscrape import API
from feedgen.feed import FeedGenerator
import sqlite3
from datetime import datetime
import asyncio

app = FastAPI()
api = API()

conn = sqlite3.connect("rss.db", check_same_thread=False)

conn.execute("""
CREATE TABLE IF NOT EXISTS seen (
    query TEXT PRIMARY KEY,
    last_id INTEGER
)
""")
conn.commit()


@app.get("/rss")
async def rss(query: str):

    row = conn.execute(
        "SELECT last_id FROM seen WHERE query=?",
        (query,)
    ).fetchone()

    since_id = row[0] if row else 0

    tweets = []

    async for tweet in api.search(query, limit=20):

        if tweet.id <= since_id:
            continue

        tweets.append(tweet)

    if tweets:

        max_id = max(t.id for t in tweets)

        conn.execute(
            "INSERT OR REPLACE INTO seen(query,last_id) VALUES(?,?)",
            (query, max_id)
        )

        conn.commit()

    fg = FeedGenerator()

    fg.title(f"X RSS: {query}")
    fg.link(href=f"https://x.com/search?q={query}")
    fg.description("Generated RSS feed")

    for tweet in reversed(tweets):

        fe = fg.add_entry()

        fe.id(str(tweet.id))
        fe.title(tweet.rawContent[:100])

        fe.link(
            href=f"https://x.com/{tweet.user.username}/status/{tweet.id}"
        )

        fe.description(tweet.rawContent)

        fe.pubDate(
            datetime.fromtimestamp(tweet.date.timestamp())
        )

    rss_feed = fg.rss_str(pretty=True)

    return Response(
        content=rss_feed,
        media_type="application/rss+xml"
    )
