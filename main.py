import datetime
import re
import urllib
import urllib2

from google.appengine.api import urlfetch
from google.appengine.ext import ndb
#from google.cloud import logging

import webapp2

from flask import Flask
app = Flask(__name__)
app.config['DEBUG'] = True

#logging_client = logging.Client()
#logger = logging_client.logger('log')

# Note: We don't need to call run() since our application is embedded within
# the App Engine WSGI application server.

class Beer(ndb.Model):
	id = ndb.StringProperty()
	name = ndb.StringProperty()
	baRating = ndb.StringProperty()
	last_update = ndb.DateTimeProperty()


def FetchPage(url):
	page = None
	try:
		req = urllib2.Request(url, headers={'User-Agent' : "Magic Browser"})
		con = urllib2.urlopen(req)
		page = con.read()
	except urllib2.URLError as e:
		raise e
	return page


def GetFirstMatch(html, pattern):
	pattern_re = re.compile(pattern)
	result = pattern_re.search(html)
	if result:
		return result.groups()[0]
	return None


@app.route('/')
def hello():
    """Return a friendly HTTP greeting."""
    return 'Hello World!'
 

@app.route('/reset')
def reset():
 	"""Clear database."""
 	beers = Beer.query().fetch()
 	ndb.delete_multi([beer.key for beer in beers])
 	return 'Database Reset'

@app.route('/iscached/<beer_name>')
def isCached(beer_name):
	beers = Beer.query(Beer.name == beer_name).fetch()
	if beers:
		return 'true'
	return 'false'

@app.route('/beer/<beer_name>')
def getBeer(beer_name):
	# First check cache for results.
	beers = Beer.query(Beer.name == beer_name).fetch()
	if beers:
		#logger.log_text('Received call for %s, result is cached.' % beer_name) 
		return beers[0].baRating

	#logger.log_text('Received call for %s, querying beeradvocate.' % beer_name) 
	baBaseUrl = 'http://www.beeradvocate.com'

	search_url = baBaseUrl + '/search/?' + urllib.urlencode({'qt': 'beer', 'q': beer_name})
	page = FetchPage(search_url)
	# Some sort of error, ideally we retry here or something.
	if not page: return '0'

	# This is the search landing page -- get page for beer.
	beer_url = GetFirstMatch(page, '<a href="(/beer/profile/.*?)">')
	if not beer_url: return '0'

	# This is the page that contains the rating -- scrape it.
	beer_url = baBaseUrl + beer_url
	ratings_page = FetchPage(beer_url)
	if not ratings_page: return
	rating = GetFirstMatch(ratings_page, '<span class="ba-ravg">(.*?)</span>')
	if not rating: return '0'
	if rating == '-' or rating == '':
		rating = '0'

	# Cache results.
	Beer(name=beer_name, baRating=rating, last_update=datetime.datetime.now()).put()
	return rating