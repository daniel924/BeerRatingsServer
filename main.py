import re
import urllib
import urllib2

from google.appengine.api import urlfetch

import webapp2

from flask import Flask
app = Flask(__name__)
app.config['DEBUG'] = True

# Note: We don't need to call run() since our application is embedded within
# the App Engine WSGI application server.

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
  

@app.route('/beer/<beer>')
def getBeer(beer):
	baBaseUrl = 'http://www.beeradvocate.com'

	search_url = baBaseUrl + '/search/?' + urllib.urlencode({'qt': 'beer', 'q': beer})
	page = FetchPage(search_url)
	# Some sort of error, ideally we retry here or something.
	if not page: return '0'

	beer_url = GetFirstMatch(page, '<a href="(/beer/profile/.*?)">')
	if not beer_url: return '0'

	beer_url = baBaseUrl + beer_url
	ratings_page = FetchPage(beer_url)
	if not ratings_page: return
	rating = GetFirstMatch(ratings_page, '<span class="ba-ravg">(.*?)</span>')
	if not rating: return '0'
	if rating == '-' or rating == '':
		rating = '0'
	return rating
