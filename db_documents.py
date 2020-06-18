from mongoengine import (
    connect, Document,
    ReferenceField,
    StringField, ListField,
    DateTimeField, BooleanField, IntField)


tweet_document_indexes = [
    'tweet_text',
    'tweet_id', 'urls', 'link',
    'is_retweet', 'votes', 'tweet_date',
    'username', 'user_id', 'profile_image_url', 'date_updated',
    'is_queried_tweet', 'conversation_id', 'paper'
]

paper_document_indexes = [
    'title', 'doi',
    'pubmed_id', 'pmcid', 'weight'
]

top_tweet_document_indexes = [
    'tweet',
    'date_updated', 'paper'
]

top_paper_document_indexes = [
    'title', 'doi',
    'pubmed_id', 'pmcid', 'weight'
]


class PaperDocument(Document):
    # Paper information
    title = StringField(default=None)
    doi = StringField(default=None)
    pubmed_id = StringField(default=None)
    pmcid = StringField(default=None)

    # Weight of paper so that it can be ranked amongst other papers
    weight = IntField(required=True)


class TweetDocument(Document):
    # Tweet information
    tweet_text = StringField(required=True)
    tweet_id = StringField(required=True)
    urls = ListField(StringField(required=True), default=lambda: [])
    link = StringField(required=True)
    is_retweet = BooleanField(required=True)
    votes = IntField(default=None)
    tweet_date = DateTimeField(required=True)

    # User information
    username = StringField(required=True)
    user_id = StringField(required=True)
    profile_image_url = StringField(required=True)

    date_updated = DateTimeField(required=True)
    is_queried_tweet = BooleanField(required=True)

    # Thread id
    conversation_id = StringField(required=True)

    # Paper that the tweet mentions
    paper = ReferenceField(PaperDocument)


class TopPaperDocument(Document):
    # Paper information
    title = StringField(default=None)
    doi = StringField(default=None)
    pubmed_id = StringField(default=None)
    pmcid = StringField(default=None)

    # Weight of paper so that it can be ranked amongst other papers
    weight = IntField(required=True)


class TopTweetDocument(Document):
    tweet = ReferenceField(TweetDocument)
    date_updated = DateTimeField(required=True)
    paper = ReferenceField(TopPaperDocument)
