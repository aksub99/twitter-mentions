import twint
import re
import math
import json
import pandas as pd
from pymongo import MongoClient
from datetime import datetime, timedelta


class TwitterMentions:
    
    def setup_db(self):
        self.db = MongoClient().twitter_db
        self.collection = self.db['Twitter_mentions']

    def query_paper_identifiers(self, title, doi, pubmed_id, pmcid):
        # Query tweets with title, doi, pubmed_id and pmcid
        if title == None:
            tweets_title = []
        else:
            tweets_title = self.query(title)

        if doi == None:
            tweets_doi = []
        else:
            tweets_doi = self.query(doi)

        if pubmed_id == None:
            tweets_pubmed_id = []
        else:
            tweets_pubmed_id = self.query(pubmed_id)

        if pmcid == None:
            tweets_pmcid = []
        else:
            tweets_pmcid = self.query(pmcid)

        # Add up all tweets
        tweets_list_query = tweets_title + tweets_doi + tweets_pubmed_id + tweets_pmcid
        self.get_tweet_info(tweets_list_query, title, doi, pubmed_id, pmcid)

    def query(self, query):
        tweets = []
        c = twint.Config()
        c.Search = query
        c.Lang = 'en'
        c.Store_object = True
        c.Store_object_tweets_list = tweets
        twint.run.Search(c)

        return tweets

    def get_votes_and_profile_image(self, tweet, full_thread_text, title, doi, pubmed_id, pmcid):
        # Inspired by https://github.com/karpathy/arxiv-sanity-preserver
        def tprepro(tweet_text):
            # take tweet, return set of words
            t = tweet_text.lower()
            t = re.sub(r'[^\w\s@]','',t) # remove punctuation
            ws = set([w for w in t.split() if not (w.startswith('#') or w.startswith('@'))])
            return ws
        
        # Lookup the profile of the user
        users_list = []
        c = twint.Config()
        c.Username = tweet.username
        c.Store_object = True
        c.Store_object_users_list = users_list
        twint.run.Lookup(c)

        # Get number of followers and profile image url
        num_followers = users_list[0].followers
        profile_image_url = users_list[0].avatar

        # Give low weight to retweets, tweets without comments and tweets with short length
        thread_words = set()
        for part in full_thread_text:
            thread_words = thread_words | tprepro(part)

        query_words = set()
        for identifier in [title, doi, pubmed_id, pmcid]:
            if identifier is not None:
                query_words = query_words | tprepro(identifier)

        for url in tweet.urls:
            query_words = query_words | tprepro(url)

        comments = thread_words - query_words
        isok = int(not(tweet.retweet or len(tweet.tweet) < 40) and len(comments) >= 5)
        tweet_sort_bonus = 10000 if isok else 0

        # Add up all contributing factors
        votes = int(tweet.likes_count) + int(tweet.retweets_count) + tweet_sort_bonus + num_followers

        return votes, profile_image_url

    def get_tweet_info(self, tweets, title, doi, pubmed_id, pmcid):
        for tweet in tweets:
            is_first_tweet_in_thread = True
            if int(tweet.conversation_id) != int(tweet.id):
                is_first_tweet_in_thread = False

            full_thread_text = self.unroll_thread(tweet, is_first_tweet_in_thread)
            votes, profile_image_url = self.get_votes_and_profile_image(tweet, full_thread_text, title, doi, pubmed_id, pmcid)

            tweet_info = {}
            tweet_info['Thread_text'] = full_thread_text
            tweet_info['Tweet_text'] = [tweet.tweet]
            tweet_info['Tweet_id'] = tweet.id_str
            tweet_info['Username'] = tweet.username
            tweet_info['User_id'] = tweet.user_id_str
            tweet_info['Urls'] = tweet.urls
            tweet_info['Link'] = tweet.link
            tweet_info['Is_retweet'] = tweet.retweet
            tweet_info['Title'] = title
            tweet_info['Doi'] = doi
            tweet_info['Pubmed_id'] = pubmed_id
            tweet_info['Pmcid'] = pmcid
            tweet_info['Profile_image_url'] = profile_image_url
            tweet_info['Votes'] = votes
            tweet_info['Doi'] = doi
            tweet_info['Tweet_date'] = datetime.fromisoformat(tweet.datestamp + ' ' + tweet.timestamp)
            tweet_info['Date_updated'] = datetime.now()

            self.collection.insert_one(tweet_info)

    def unroll_thread(self, tweet, is_first_tweet_in_thread):
        tweets_list_user = []
        c = twint.Config()
        c.Username = tweet.username
        if not is_first_tweet_in_thread:
            c.Since = str(datetime.fromisoformat(tweet.datestamp + ' ' + tweet.timestamp) - timedelta(hours=10))
            c.Until = str(datetime.fromisoformat(tweet.datestamp + ' ' + tweet.timestamp) + timedelta(hours=10))
        else:
            c.Since = str(datetime.fromisoformat(tweet.datestamp + ' ' + tweet.timestamp))
            c.Until = str(datetime.fromisoformat(tweet.datestamp + ' ' + tweet.timestamp) + timedelta(hours=30))
        c.Lang = 'en'
        c.Store_object = True
        c.Store_object_tweets_list = tweets_list_user
        twint.run.Search(c)

        conversation_tweets = []
        for tw in tweets_list_user:
            if tw.conversation_id == tweet.conversation_id:
                conversation_tweets.append(tw.tweet)

        return conversation_tweets[::-1]

    def main(self):
        self.setup_db()
        json_file = open("categorized_abstract.json")
        papers = json.load(json_file)
        for paper in papers:
            title = paper['title']
            doi = paper['doi']
            pubmed_id = paper['pubmed_id']
            pmcid = paper['pmcid']

            self.query_paper_identifiers(title, doi, pubmed_id, pmcid)


if __name__ == "__main__":
    obj = TwitterMentions()
    obj.main()
