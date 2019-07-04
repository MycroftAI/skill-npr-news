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

import feedparser
import re
import os
import subprocess

from adapt.intent import IntentBuilder
from mycroft.audio import wait_while_speaking
from mycroft.skills.core import intent_handler, intent_file_handler
from mycroft.skills.common_play_skill import CommonPlaySkill, CPSMatchLevel
from mycroft.util import get_cache_directory
import traceback
from requests import Session

# NOTE: This has to be in synch with the settingsmeta options
# TODO: Better language support -- this mixes new sources regardless of languages
FEEDS = {
    "other" : ("your custom feed", None),
    "custom" : ("your custom feed", None),
    "BBC" : ("BBC News", "http://podcasts.files.bbci.co.uk/p02nq0gn.rss"),
    "NPR" : ("NPR News Now", "http://www.npr.org/rss/podcast.php?id=500005"),
    "AP" :  ("AP Hourly Radio News", "http://www.spreaker.com/show/1401466/episodes/feed"),
    "CBC" : ("CBC.ca News", "http://www.cbc.ca/podcasting/includes/hourlynews.xml"),
    "FOX" : ("Fox News", "http://feeds.foxnewsradio.com/FoxNewsRadio"),
    "PBS" : ("PBS NewsHour", "https://www.pbs.org/newshour/feeds/rss/podcasts/show"),
    "YLE" : ("YLE", "https://feeds.yle.fi/areena/v1/series/1-1440981.rss"),
    "DLF" : ("DLF", "https://www.deutschlandfunk.de/podcast-nachrichten.1257.de.podcast.xml"),
    "WDR" : ("WDR",
        "https://www1.wdr.de/mediathek/audio/wdr-aktuell-news/wdr-aktuell-152.podcast"),
    "Ekot" : ("Ekot", "https://api.sr.se/api/rss/pod/3795"),
    "ABC" : ("ABC News Australia", "https://rss.whooshkaa.com/rss/podcast/id/2381")
}


def find_mime(url):
    mime = 'audio/mpeg'
    response = Session().head(url, allow_redirects=True)
    if 200 <= response.status_code < 300:
        mime = response.headers['content-type']
    return mime

class NewsSkill(CommonPlaySkill):
    def __init__(self):
        super().__init__(name="NewsSkill")
        self.curl = None
        self.now_playing = None
        self.STREAM = '{}/stream'.format(get_cache_directory('NewsSkill'))

    def CPS_match_query_phrase(self, phrase):
        # Look for a specific news provider
        phrase = ' '.join(phrase.lower().split())
        for source in FEEDS:
            if source.lower() in phrase:
                if self.voc_match(phrase, "News"):
                    return (source + " news", CPSMatchLevel.EXACT,
                            {"feed": source})
                else:
                    return (source, CPSMatchLevel.TITLE,
                            {"feed": source})

        if self.voc_match(phrase, "News"):
            return ("news", CPSMatchLevel.TITLE)

    def CPS_start(self, phrase, data):
        if data and "feed" in data:
            # Play the requested news service
            self.handle_latest_news(feed=data["feed"])
        else:
            # Just use the default news feed
            self.handle_latest_news()

    def get_rss(self, url=None):
        url_rss = url
        if not url_rss:
            pre_select = self.settings.get("pre_select", "")
            url_rss = self.settings.get("url_rss")
            if "not_set" in pre_select:
                # Use a custom RSS URL
                url_rss = self.settings.get("url_rss")
                self.now_playing = None
            else:
                # Use the selected preset's URL
                url_rss = pre_select
                # Look for the title
                for feed in FEEDS:
                    if FEEDS[feed][1] == url_rss:
                        self.now_playing = FEEDS[feed][0]

        if not url_rss:
            # Default to NPR News
            self.now_playing = FEEDS["NPR"][0]
            url_rss = FEEDS["NPR"][1]
        return url_rss

    def get_feed(self, url_rss):
        data = feedparser.parse(url_rss.strip())
        # After the intro, find and start the news stream
        # select the first link to an audio file
        for link in data['entries'][0]['links']:
            if 'audio' in link['type']:
                media = link['href']
                break
        else:
            # fall back to using the first link in the entry
            media = data['entries'][0]['links'][0]['href']
        self.log.info('Playing news from URL: '+media)
        return media

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

    @intent_handler(IntentBuilder("").require("Latest").require("News"))
    def handle_latest_news(self, message=None, feed=None):
        try:
            self.stop()

            rss = None
            self.now_playing = None
            if feed and feed in FEEDS:
                self.now_playing = FEEDS[feed][0]
                rss = FEEDS[feed][1]

            # Speak intro while downloading in background
            rss = self.get_rss(rss)
            self.speak_dialog('news', data={"from": self.now_playing})

            url = self.get_feed(rss)
            mime = find_mime(url)
            # (Re)create Fifo
            if os.path.exists(self.STREAM):
                os.remove(self.STREAM)
            os.mkfifo(self.STREAM)

            self.log.debug('Running curl {}'.format(url))
            self.curl = subprocess.Popen(
                'curl -L "{}" > {}'.format(url, self.STREAM),
                shell=True)

            # Show news title, if there is one
            wait_while_speaking()
            # Begin the news stream
            self.CPS_play(('file://' + self.STREAM, mime))

        except Exception as e:
            self.log.error("Error: {0}".format(e))
            self.log.debug("Traceback: {}".format(traceback.format_exc()))
            self.speak_dialog("could.not.start.the.news.feed")

    def stop(self):
        # Stop download process if it's running.
        if self.curl:
            try:
                self.curl.kill()
                self.curl.communicate()
            except Exception as e:
                self.log.error('Could not stop curl: {}'.format(repr(e)))
            finally:
                self.curl = None
            return True


def create_skill():
    return NewsSkill()
