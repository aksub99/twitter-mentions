"""
Contains a class that supports retrieval of tweets mentioning papers papers.
"""

import twint
import re
import json
from datetime import datetime, timedelta
from tweet_document import TweetDocument
from mongoengine import connect


class TwitterMentions(object):
    """
    Class that supports retrieval of tweets mentioning papers.
    """
    
    def setup_db(self):
        """
        Connect to mongod server.
        """
        connect()

    def query_paper_identifiers(self, title, doi, pubmed_id, pmcid, fetch_threads):
        """
        Query tweets with title, doi, pubmed_id and pmcid.
        """
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

        # Add up all tweets belonging to the current paper
        tweets_list_query = tweets_title + tweets_doi + tweets_pubmed_id + tweets_pmcid
        self.get_tweet_info(tweets_list_query, title, doi, pubmed_id, pmcid, fetch_threads)

    def query(self, query):
        """
        Search for tweets that contain "query".
        """
        tweets = []
        c = twint.Config()
        c.Search = '"' + query + '"'
        c.Lang = 'en'
        c.Store_object = True
        c.Store_object_tweets_list = tweets
        twint.run.Search(c)

        return tweets

    def get_votes_and_profile_image(self, tweet, full_thread_text=None, title=None, doi=None, pubmed_id=None, pmcid=None, return_votes=True):
        """
        Get profile image of tweeter and compute votes of tweet.
        """
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
        bio = users_list[0].bio

        if return_votes == False:
            return None, profile_image_url

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

        research_bonus = 0
        # If bio contains keywords such as research/professor, give additional points
        if re.search(r'.*researcher.*', bio, re.IGNORECASE) or re.search(r'.*professor.*', bio, re.IGNORECASE) or re.search(r'.*phd.*', bio, re.IGNORECASE) or re.search(r'.*postdoc.*', bio, re.IGNORECASE) or re.search(r'.*scientist.*', bio, re.IGNORECASE):
            research_bonus += 500

        # Add up all contributing factors
        votes = int(tweet.likes_count) + int(tweet.retweets_count) + tweet_sort_bonus + num_followers + research_bonus

        return votes, profile_image_url

    def save_document(self, tweet, profile_image_url,
                      title, doi, pubmed_id, pmcid, is_queried_tweet, votes=None):
        """
        Save document into mongodb database.
        """
        try:
            TweetDocument.objects.get(tweet_id=tweet.id_str)
        except:
            TweetDocument(tweet_text=tweet.tweet, tweet_id=tweet.id_str, urls=tweet.urls, link=tweet.link,
                          is_retweet=tweet.retweet, votes=votes, tweet_date=datetime.fromisoformat(tweet.datestamp + ' ' + tweet.timestamp),
                          username=tweet.username, user_id=tweet.user_id_str, profile_image_url=profile_image_url, title=title,
                          doi=doi, pubmed_id=pubmed_id, pmcid=pmcid, date_updated=datetime.now(),
                          conversation_id=tweet.conversation_id, is_queried_tweet=is_queried_tweet).save()

    def get_thread_tweets_info(self, thread_tweets, thread_text, title, doi, pubmed_id, pmcid, queried_tweet_id):
        """
        Loop through all tweets in a thread and save in database.
        """
        for tweet in thread_tweets:
            is_queried_tweet = False
            return_votes = False

            if tweet.id == queried_tweet_id:
                is_queried_tweet = True
                return_votes = True
                votes, profile_image_url = self.get_votes_and_profile_image(tweet, thread_text, title, doi, pubmed_id, pmcid, return_votes=return_votes)
            else:
                votes, profile_image_url = self.get_votes_and_profile_image(tweet, return_votes=return_votes)

            self.save_document(tweet, profile_image_url, title, doi, pubmed_id, pmcid, is_queried_tweet, votes)

    def get_tweet_info(self, tweets, title, doi, pubmed_id, pmcid, fetch_threads):
        """
        Loop through tweets and collect information required in database.
        """
        for tweet in tweets:
            if not fetch_threads:
                # If we want just the queried tweets
                is_queried_tweet = True
                votes, profile_image_url = self.get_votes_and_profile_image(tweet, [tweet.tweet], title, doi, pubmed_id, pmcid, return_votes=True)
                self.save_document(tweet, profile_image_url, title, doi, pubmed_id, pmcid, is_queried_tweet, votes)
            else:
                # If we want to unroll threads
                queried_tweet_id = tweet.id
                is_first_tweet_in_thread = True
                if int(tweet.conversation_id) != int(tweet.id):
                    is_first_tweet_in_thread = False

                # Unroll threads
                thread_tweets, thread_text = self.unroll_thread(tweet, is_first_tweet_in_thread)
                self.get_thread_tweets_info(thread_tweets, thread_text, title, doi, pubmed_id, pmcid, queried_tweet_id)

    def unroll_thread(self, tweet, is_first_tweet_in_thread):
        """
        Unroll thread.
        """
        tweets_list_user = []
        c = twint.Config()
        c.Search = "@" + tweet.username
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
        conversation_tweets_text = []
        for tw in tweets_list_user:
            if tw.conversation_id == tweet.conversation_id:
                conversation_tweets.append(tw)
                conversation_tweets_text.append(tw.tweet)

        return conversation_tweets[::-1], conversation_tweets_text[::-1]

    def main(self):
        # Connect to mongod
        self.setup_db()

        # Json containing paper information
        json_file = open("categorized_abstract.json")
        papers = json.load(json_file)

        # Do we want to fetch the threads?
        fetch_threads = False

        for paper in papers:
            title = paper['title']
            doi = paper['doi']
            pubmed_id = paper['pubmed_id']
            pmcid = paper['pmcid']

            self.query_paper_identifiers(title, doi, pubmed_id, pmcid, fetch_threads)


if __name__ == "__main__":
    obj = TwitterMentions()
    obj.main()
