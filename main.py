import datetime
import json
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

BEERMENUS_URL = 'https://www.beermenus.com'

class Beer(ndb.Model):
	id = ndb.StringProperty()
	name = ndb.StringProperty()
	baRating = ndb.StringProperty()
	last_update = ndb.DateTimeProperty()

class Place(ndb.Model):
	id = ndb.StringProperty()
	name = ndb.StringProperty()
	url = ndb.StringProperty()
	beers = ndb.StringProperty(repeated=True)
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
 	ndb.delete_multi([b.key for b in beers])
 	places = Place.query().fetch()
 	ndb.delete_multi([p.key for p in places])
 	return 'Database Reset'

@app.route('/iscached/<beer_name>')
def isCached(beer_name):
	beers = Beer.query(Beer.name == beer_name).fetch()
	if beers:
		return 'true'
	return 'false'

def IsFreshData(cached_result):
	return cached_result.last_update.date() == datetime.datetime.now().date()

def _getBeersFromPlace(place):
	# First check cache for results.
	menu_url = None
	cached_menu = Place.query(Place.name == place).fetch()
	if cached_menu:
		if IsFreshData(cached_menu[0]):
			print 'Returning cached menus'
			return cached_menu[0].beers
		else:
			menu_url = cached_menu[0].url

	if not menu_url:
		search_url = BEERMENUS_URL + '/search?' + urllib.urlencode({'q': place})
		page = FetchPage(search_url)
		if not page: return
		menu_url = GetFirstMatch(page, '<a href="(/places/.*?)">')

	# Now that we have the place url, search for the beers.
	beer_page = FetchPage(BEERMENUS_URL + menu_url)
	beers = set()
	for match in re.finditer('<a href="/beers/.*?">(.*)?</a>', beer_page):
		beer = match.groups()[0]
		# We check for the 'more' string because it can accidentally match 
		# the regex.
		if beer != 'more': beers.add(beer)
	Place(name=place, url=menu_url, beers=beers, 
		  last_update=datetime.datetime.now()).put()
	return list(beers)

@app.route('/place/<place>')
def getBeersFromPlace(place):
	return json.dumps(_getBeersFromPlace(place))

@app.route('/beer2/<beer_name>')
def getBeer(beer_name):
	# First check cache for results.
	cached_beers = Beer.query(Beer.name == beer_name).fetch()
	if cached_beers:
		#logger.log_text('Received call for %s, result is cached.' % beer_name) 
		if cached_beers[0].last_update.date() == datetime.datetime.now().date():
			return cached_beers[0].baRating
		else:
			cached_beers[0].key.delete()


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

@app.route('/beer/<beer_name>')
def getBeerFromGoogle(beer_name):
	# First check cache for results.
	cached_beers = Beer.query(Beer.name == beer_name).fetch()
	if cached_beers:
		#logger.log_text('Received call for %s, result is cached.' % beer_name) 
		if cached_beers[0].last_update.date() == datetime.datetime.now().date():
			print 'Returning cached beer rating'
			return cached_beers[0].baRating
		else:
			cached_beers[0].key.delete()

	google_base_url = 'http://www.google.com'
	search_url = google_base_url + '/search?' + urllib.urlencode({'q': beer_name + ' site:beeradvocate.com'})
	page = FetchPage(search_url)
	# Some sort of error, ideally we retry here or something.
	if not page: return '0'

	rating = GetFirstMatch(page, 'Rating: (.*?)&nbsp')
	if not rating: return '0'
	if rating == '-' or rating == '':
		rating = '0'

	# Cache results.
	Beer(name=beer_name, baRating=rating, last_update=datetime.datetime.now()).put()
	return rating


@app.route('/all/<place>')
def getAll(place):
	beer_names = _getBeersFromPlace(place)
	beers = []
	for name in beer_names:
		baRating = getBeerFromGoogle(name)
		beers.append({'name': name, 'baRating': baRating})
	return json.dumps(beers)