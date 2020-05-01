# Copyright 2018 Mycroft AI Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from datetime import date, timedelta
import feedparser
import os
from os.path import join, abspath, dirname
import re
import requests
import subprocess
import time
import traceback
from urllib.parse import quote
from urllib.request import urlopen
from bs4 import BeautifulSoup
from pytz import timezone

from adapt.intent import IntentBuilder
from mycroft.audio import wait_while_speaking
from mycroft.messagebus.message import Message
from mycroft.skills.core import intent_handler, intent_file_handler
from mycroft.skills.common_play_skill import CommonPlaySkill, CPSMatchLevel
from mycroft.util import get_cache_directory
from mycroft.util.parse import fuzzy_match
from mycroft.util.time import now_local


def image_path(filename):
    return 'file://' + join(dirname(abspath(__file__)), 'images', filename)


def tsf():
    """Custom inews fetcher for TSF news."""
    feed = ('https://www.tsf.pt/stream/audio/{year}/{month:02d}/'
            'noticias/{day:02d}/not{hour:02d}.mp3')
    uri = None
    i = 0
    status = 404
    date = now_local(timezone('Portugal'))
    while status != 200 and i < 5:
        date -= timedelta(hours=i)
        uri = feed.format(hour=date.hour, year=date.year,
                          month=date.month, day=date.day)
        status = requests.get(uri).status_code
        i += 1
    if status != 200:
        return None
    return uri


def gbp():
    """Custom news fetcher for GBP news."""
    feed = 'http://feeds.feedburner.com/gpbnews/GeorgiaRSS?format=xml'
    data = feedparser.parse(feed)
    next_link = None
    for entry in data['entries']:
        # Find the first mp3 link with "GPB {time} Headlines" in title
        if 'GPB' in entry['title'] and 'Headlines' in entry['title']:
            next_link = entry['links'][0]['href']
            break
    html = requests.get(next_link)
    # Find the first mp3 link
    # Note that the latest mp3 may not be news,
    # but could be an interview, etc.
    mp3_find = re.search(r'href="(?P<mp3>.+\.mp3)"'.encode(), html.content)
    if mp3_find is None:
        return None
    url = mp3_find.group('mp3').decode('utf-8')
    return url


def ft():
    """Custom news fetcher for today's FT news briefing"""
    url = 'https://www.ft.com/newsbriefing'
    page = urlopen(url)

    # Use bs4 to parse website and get mp3 link
    soup = BeautifulSoup(page, features='html.parser')
    result = soup.find('time')

    # Check if div matches today's date
    if datetime.strptime(result.contents[0], '%A, %d %B, %Y').date() == datetime.now().date():
        target_div = result.parent.find_next('div')
        target_url = 'http://www.ft.com' + target_div.a['href']

        mp3_url = target_url
        mp3_page = urlopen(mp3_url)
        mp3_soup = BeautifulSoup(mp3_page, features='html.parser')

        return mp3_soup.find('source')['src']


"""Feed Tuple:
    Key: Station acronym or short title
    Tuple: (
        Long title (String),
        Feed url (String) or custom function name defined above,
        image_path - for use on Mycroft GUI
        )
    NOTE - this list has to be in sync with the settingsmeta select options"""
FEEDS = {
    'other': ('Your custom feed', None, None),
    'custom': ('Your custom feed', None, None),
    'ABC': ('ABC News Australia',
            'https://rss.whooshkaa.com/rss/podcast/id/2381',
            image_path('ABC.png')),
    'AP':  ('AP Hourly Radio News',
            "https://www.spreaker.com/show/1401466/episodes/feed",
            image_path('AP.png')),
    'BBC': ('BBC News', 'https://podcasts.files.bbci.co.uk/p02nq0gn.rss',
            image_path('BBC.png')),
    'CBC': ('CBC News',
            'https://www.cbc.ca/podcasting/includes/hourlynews.xml',
            image_path('CBC.png')),
    'DLF': ('DLF', 'https://www.deutschlandfunk.de/'
                   'podcast-nachrichten.1257.de.podcast.xml',
            image_path('DLF')),
    'Ekot': ('Ekot', 'https://api.sr.se/api/rss/pod/3795',
             image_path('Ekot.png')),
    'FOX': ('Fox News', 'http://feeds.foxnewsradio.com/FoxNewsRadio',
            image_path('FOX.png')),
    'NPR': ('NPR News Now', 'https://www.npr.org/rss/podcast.php?id=500005',
            image_path('NPR.png')),
    'PBS': ('PBS NewsHour', 'https://www.pbs.org/newshour/feeds/'
                            'rss/podcasts/show',
            image_path('PBS.png')),
    'VRT': ('VRT Nieuws', 'https://progressive-audio.lwc.vrtcdn.be/'
                          'content/fixed/11_11niws-snip_hi.mp3',
            None),
    'WDR': ('WDR', 'https://www1.wdr.de/mediathek/audio/'
                   'wdr-aktuell-news/wdr-aktuell-152.podcast',
            image_path('WDR')),
    'YLE': ('YLE', 'https://feeds.yle.fi/areena/v1/series/1-1440981.rss',
            image_path('Yle.png')),
    "GBP": ("Georgia Public Radio", gbp, None),
    "RDP": ("RDP Africa", "http://www.rtp.pt//play/itunes/5442", None),
    "RNE": ("National Spanish Radio",
            "http://api.rtve.es/api/programas/36019/audios.rs", None),
    "TSF": ("TSF Radio", tsf, None),
    "OE3": ("Ö3 Nachrichten",
            "https://oe3meta.orf.at/oe3mdata/StaticAudio/Nachrichten.mp3",
            None),
    "FT": ("Financial Times", ft, None),
}


# If feed URL ends in specific filetype, just play it
DIRECT_PLAY_FILETYPES = ['.mp3']


def find_mime(url):
    mime = 'audio/mpeg'
    response = requests.Session().head(url, allow_redirects=True)
    if 200 <= response.status_code < 300:
        mime = response.headers['content-type']
    return mime


class NewsSkill(CommonPlaySkill):
    def __init__(self):
        super().__init__(name="NewsSkill")
        self.curl = None
        self.now_playing = None
        self.last_message = None
        self.STREAM = '{}/stream'.format(get_cache_directory('NewsSkill'))

    def initialize(self):
        time.sleep(1)
        self.log.debug('Disabling restart intent')
        self.disable_intent('restart_playback')
        # Default feed per country code, if user has not selected a default
        self.default_feed = self.translate_namedvalues('country.default')
        # Longer titles or alternative common names of feeds for searching
        self.alt_feed_names = self.translate_namedvalues('alt.feed.name')

    def CPS_match_query_phrase(self, phrase):
        matched_feed = { 'key': None, 'conf': 0.0 }

        # Remove "the" as it matches too well will "other"
        search_phrase = phrase.lower().replace('the', '')
        
        # Catch any short explicit phrases eg "play the news"
        news_phrases = self.translate_list("PlayTheNews") or []
        if search_phrase.strip() in news_phrases:
            station_key = self.settings.get("station", "not_set")
            if station_key == "not_set":
                station_key = self.get_default_station()
            matched_feed = { 'key': station_key, 'conf': 1.0 }        

        def match_feed_name(phrase, feed):
            """ Determine confidence that a phrase requested a given feed.

                    Args:
                       phrase (str): utterance from the user
                       feed (str): the station feed to match against

                    Returns:
                        tuple: feed being matched, confidence level
            """
            phrase = phrase.lower().replace("play", "")
            feed_short_name = feed.lower()
            short_name_confidence = fuzzy_match(phrase, feed_short_name)
            long_name_confidence = fuzzy_match(phrase, FEEDS[feed][0].lower())
            # Test with "News" added in case user only says acronym eg "ABC".
            # As it is short it may not provide a high match confidence.
            news_keyword = self.translate("OnlyNews").lower()
            modified_short_name = "{} {}".format(feed_short_name, news_keyword)
            variation_confidence = fuzzy_match(phrase, modified_short_name)
            key_confidence = 0.6 if news_keyword in phrase and feed_short_name in phrase else 0.0


            conf = max((short_name_confidence, long_name_confidence,
                        variation_confidence, key_confidence))
            return feed, conf

        # Check primary feed list for matches eg 'ABC'
        for feed in FEEDS:
            feed, conf = match_feed_name(search_phrase, feed)
            if conf > matched_feed['conf']:
                matched_feed['conf'] = conf
                matched_feed['key'] = feed

        # Check list of alternate names eg 'associated press' => 'AP'
        for name in self.alt_feed_names:
            conf = fuzzy_match(search_phrase, name)
            if conf > matched_feed['conf']:
                matched_feed['conf'] = conf
                matched_feed['key'] = self.alt_feed_names[name]
            
        # If no match but utterance contains news, return low confidence level
        if matched_feed['conf'] == 0.0 and self.voc_match(search_phrase, "News"):
            matched_feed = { 'key': None, 'conf': 0.5 }

        feed_title = FEEDS[matched_feed['key']][0]
        if matched_feed['conf'] >= 0.9:
            match_level = CPSMatchLevel.EXACT  
        elif matched_feed['conf'] >= 0.7:
            match_level = CPSMatchLevel.ARTIST
        elif matched_feed['conf'] >= 0.5:
            match_level = CPSMatchLevel.CATEGORY
        else: 
            match_level = None
            return match_level
        feed_data = { 'feed': matched_feed['key']}

        return (feed_title, match_level, feed_data)

    def CPS_start(self, phrase, data):
        if data and data.get("feed"):
            # Play the requested news service
            self.handle_latest_news(feed=data["feed"])
        else:
            # Just use the default news feed
            self.handle_latest_news()

    def get_default_station(self):
        country_code = self.location['city']['state']['country']['code']
        if self.default_feed.get(country_code) is not None:
            feed_code = self.default_feed[country_code]
        else:
            feed_code = "NPR"
        return feed_code

    def get_station(self):
        """ Get station to play. Prioritise selected station, then custom url.
        If neither exist then fallback to default station for country. """
        feed_code = self.settings.get("station", "not_set")
        station_url = self.settings.get("custom_url", "")
        if feed_code in FEEDS:
            title, station_url, image = FEEDS[feed_code]
        elif len(station_url) > 0:
            title = FEEDS["custom"][0]
            image = None
        else:
            feed_code = self.get_default_station()
            title, station_url, image = FEEDS[feed_code]

        return title, station_url, image

    def get_media_url(self, station_url):
        if callable(station_url):
            return station_url()

        # If link is an audio file, just play it.
        if station_url and station_url[-4:] in DIRECT_PLAY_FILETYPES:
            self.log.debug('Playing news from URL: {}'.format(station_url))
            return station_url

        # Otherwise it is an RSS or XML feed
        data = feedparser.parse(station_url.strip())
        # After the intro, find and start the news stream
        # select the first link to an audio file
        for link in data['entries'][0]['links']:
            if 'audio' in link['type']:
                media_url = link['href']
                break
            else:
                # fall back to using the first link in the entry
                media_url = data['entries'][0]['links'][0]['href']
        self.log.debug('Playing news from URL: {}'.format(media_url))
        return media_url

    @intent_file_handler("PlayTheNews.intent")
    def handle_latest_news_alt(self, message):
        # Capture some alternative ways of requesting the news via Padatious
        utt = message.data["utterance"]
        match = self.CPS_match_query_phrase(utt)
        if match and len(match) > 2:
            feed = match[2]["feed"]
        else:
            feed = None

        self.handle_latest_news(message, feed)

    @intent_handler(IntentBuilder("").one_of("Give", "Latest").require("News"))
    def handle_latest_news(self, message=None, feed=None):
        try:
            self.stop()
            rss = None
            self.now_playing = None
            # Basic check for station title in utterance
            # TODO - expand this - probably abstract from CPS Matching
            if message and not feed:
                for f in FEEDS:
                    if f.lower() in message.data["utterance"].lower():
                        feed = f
            if feed and feed in FEEDS and feed != 'other':
                self.now_playing, rss, image = FEEDS[feed]
            else:
                self.now_playing, rss, image = self.get_station()

            # Speak intro while downloading in background
            self.speak_dialog('news', data={"from": self.now_playing})

            url = self.get_media_url(rss)
            mime = find_mime(url)
            # (Re)create Fifo
            if os.path.exists(self.STREAM):
                os.remove(self.STREAM)
            os.mkfifo(self.STREAM)

            self.log.debug('Running curl {}'.format(url))
            args = ['curl', '-L', quote(url, safe=":/"), '-o', self.STREAM]
            self.curl = subprocess.Popen(args)

            # Show news title, if there is one
            wait_while_speaking()
            # Begin the news stream
            self.log.info('Feed: {}'.format(feed))
            self.CPS_play(('file://' + self.STREAM, mime))
            self.CPS_send_status(image=image or image_path('generic.png'),
                                 track=self.now_playing)
            self.last_message = (True, message)
            self.enable_intent('restart_playback')

        except Exception as e:
            self.log.error("Error: {0}".format(e))
            self.log.info("Traceback: {}".format(traceback.format_exc()))
            self.speak_dialog("could.not.start.the.news.feed")

    @intent_handler(IntentBuilder('').require('Restart'))
    def restart_playback(self, message):
        self.log.debug('Restarting last message')
        if self.last_message:
            self.handle_latest_news(self.last_message[1])

    def stop(self):
        # Disable restarting when stopped
        if self.last_message:
            self.disable_intent('restart_playback')
            self.last_message = None

        # Stop download process if it's running.
        if self.curl:
            try:
                self.curl.kill()
                self.curl.communicate()
            except Exception as e:
                self.log.error('Could not stop curl: {}'.format(repr(e)))
            finally:
                self.curl = None
            self.CPS_send_status()
            return True

    def CPS_send_status(self, artist='', track='', image=''):
        data = {'skill': self.name,
                'artist': artist,
                'track': track,
                'image': image,
                'status': None  # TODO Add status system
                }
        self.bus.emit(Message('play:status', data))


def create_skill():
    return NewsSkill()
