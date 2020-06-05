# Twitter-Mentions
- Fetches tweets that mention papers using identifiers such as Title, DOI, Pubmed ID and PMCID and stores them in a MongoDB database.
- Tweets are assigned weights based on their content and popularity so that they can be ranked among other tweets.
- Chose not to use Twitter API owing to the API call limits (we require approx. 1 call per paper) imposed and 
restricted access to old tweets (older than 7 days) through search queries.

**Note**: Install `twint` using the following commands  
`git clone https://github.com/twintproject/twint.git`  
Add the following lines to `output.py` in the `twint/twint/output.py` after line 196.
```
elif hasattr(config.Store_object_users_list, 'append'):
            config.Store_object_users_list.append(user)
```
Then install this version with `python setup.py install`
