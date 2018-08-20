import time
import csv

from selenium import webdriver
from selenium.webdriver.common.keys import Keys

browser = webdriver.Chrome()
base_url = u'https://twitter.com/search?q='
query = u'%40ismtrainierout'
url = u'https://twitter.com/IsMtRainierOut' #base_url + query

browser.get(url)
time.sleep(1)

body = browser.find_element_by_tag_name('body')

for _ in range(1000):
	body.send_keys(Keys.PAGE_DOWN)
	time.sleep(0.2)

tweets = browser.find_elements_by_class_name('tweet')
outputCsv = csv.writer(open('mountain-tweets.csv', 'w'))

for tweet in tweets:
	text = tweet.find_elements_by_class_name('js-tweet-text-container');
	picture = tweet.find_elements_by_class_name('js-adaptive-photo');

	text = text[0].text if text else False
	imageUrl = picture[0].get_attribute('data-image-url') if picture else False

	if (text and imageUrl):
		outputCsv.writerow([text, imageUrl])

browser.close()
