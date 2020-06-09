from mongoengine import (
    connect, Document,
    StringField, ListField,
    DateTimeField, BooleanField, IntField)


indexes = [
    'tweet_text',
    'tweet_id', 'username',
    'user_id',
    'urls',
    'link',
    'is_retweet',
    'title', 'doi', 'pubmed_id',
    'pmcid', 'profile_image_url',
    'votes', 'tweet_date', 'last_updated', 'conversation_id'
]


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

    # Paper information
    title = StringField(default=None)
    doi = StringField(default=None)
    pubmed_id = StringField(default=None)
    pmcid = StringField(default=None)

    date_updated = DateTimeField(required=True)
    is_queried_tweet = BooleanField(required=True)

    # Thread id
    conversation_id = StringField(required=True)