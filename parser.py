"""
Parse tweet database and create top tweets document.
"""

from mongoengine import connect
from datetime import datetime, timedelta
from db_documents import TweetDocument, PaperDocument, TopPaperDocument, TopTweetDocument


def setup_db():
    """
    Connect to mongod server.
    """
    connect()

def tweet_parser():
    """
    Choose papers that have top scores.
    """

    setup_db()

    for tweet in TweetDocument.objects.order_by('-tweet_date'):
        # Pick top scoring papers.
        if datetime.now() - timedelta(days=10) <= tweet['tweet_date']:
            if TopPaperDocument.objects(doi=tweet.paper.doi):
                top_paper = TopPaperDocument.objects.get(doi=tweet.paper.doi)
                top_paper.weight += 1
                top_paper.save()
            else:
                top_paper = TopPaperDocument(title=tweet.paper.title, doi=tweet.paper.doi, pubmed_id=tweet.paper.pubmed_id, pmcid=tweet.paper.pmcid, weight=1).save()
            TopTweetDocument(tweet=tweet, date_updated=datetime.now(), paper=top_paper).save()
        else:
            break

if __name__ == "__main__":
    tweet_parser()