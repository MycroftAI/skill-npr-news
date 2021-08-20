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

import os
import subprocess
import time
import traceback
from urllib.parse import quote

from adapt.intent import IntentBuilder
from mycroft.audio import wait_while_speaking
from mycroft.skills.core import intent_handler, intent_file_handler
from mycroft.skills.common_play_skill import CommonPlaySkill, CPSMatchLevel
from mycroft.util import get_cache_directory, LOG
from mycroft.util.parse import fuzzy_match

from .stations import stations
from .util import contains_html, find_mime_type


# Minimum confidence levels
CONF_EXACT_MATCH = 0.9
CONF_LIKELY_MATCH = 0.7
CONF_GENERIC_MATCH = 0.6

class NewsSkill(CommonPlaySkill):
    def __init__(self):
        super().__init__(name="NewsSkill")
        self.now_playing = None
        self.last_message = None
        self.curl = None
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
        matched_feed = {'key': None, 'conf': 0.0}

        # Remove "the" as it matches too well will "other"
        search_phrase = phrase.lower().replace('the', '').strip()

        if not self.voc_match(search_phrase, "News"):
            # User not asking for the news - do not match.
            return

        # Catch any short explicit phrases eg "play the news"
        news_phrases = self.translate_list("PlayTheNews") or []
        if search_phrase in news_phrases:
            station_key = self.settings.get("station", "not_set")
            if station_key == "not_set":
                station_key = self.get_default_station()
            matched_feed = {'key': station_key, 'conf': 1.0}

        def match_feed_name(phrase, feed):
            """Determine confidence that a phrase requested a given feed.

            Args:
                phrase (str): utterance from the user
                feed (str): the station feed to match against

            Returns:
                tuple: feed being matched, confidence level
            """
            phrase = phrase.lower().replace("play", "").strip()
            feed_short_name = feed.lower()
            feed_long_name = stations[feed].full_name.lower()
            short_name_confidence = fuzzy_match(phrase, feed_short_name)
            long_name_confidence = fuzzy_match(phrase, feed_long_name)
            # Test with "News" added in case user only says acronym eg "ABC".
            # As it is short it may not provide a high match confidence.
            news_keyword = self.translate("OnlyNews").lower()
            modified_short_name = "{} {}".format(feed_short_name, news_keyword)
            variation_confidence = fuzzy_match(phrase, modified_short_name)
            key_confidence = CONF_GENERIC_MATCH if news_keyword in phrase and feed_short_name in phrase else 0.0

            conf = max((short_name_confidence, long_name_confidence,
                        variation_confidence, key_confidence))
            return feed, conf

        # Check primary feed list for matches eg 'ABC'
        for feed in stations.values():
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
        if matched_feed['conf'] < CONF_GENERIC_MATCH and self.voc_match(search_phrase, "News"):
            matched_feed = {'key': self.get_default_station(),
                            'conf': CONF_GENERIC_MATCH}

        feed_title = stations[matched_feed['key']].full_name
        if matched_feed['conf'] >= CONF_EXACT_MATCH:
            match_level = CPSMatchLevel.EXACT
        elif matched_feed['conf'] >= CONF_LIKELY_MATCH:
            match_level = CPSMatchLevel.ARTIST
        elif matched_feed['conf'] >= CONF_GENERIC_MATCH:
            match_level = CPSMatchLevel.CATEGORY
        else:
            match_level = None
            return match_level
        feed_data = {'feed': matched_feed['key']}
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
        """Get station user selected from settings or default station.

        Fallback order:
        1. User selected station
        2. User defined custom url
        3. Default station for country
        """
        feed_code = self.settings.get("station", "not_set")
        station_url = self.settings.get("custom_url", "")
        if feed_code in stations.keys():
            station = stations[feed_code]
        # TODO Fix fallback to custom default
        # elif len(station_url) > 0:
        #     title = stations["custom"][0]
        #     image = None
        else:
            feed_code = self.get_default_station()
            station = stations[feed_code]

        return station

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
            station_url = None
            self.now_playing = None
            # Basic check for station title in utterance
            # TODO - expand this - probably abstract from CPS Matching
            if message and not feed:
                for station in stations:
                    if station.lower() in message.data["utterance"].lower():
                        feed = station
            if feed and feed in stations and feed != 'other':
                selected_station = stations[feed]
            else:
                selected_station = self.get_station()

            # Speak intro while downloading in background
            self.speak_dialog('news', data={"from": selected_station.full_name})
            self._play_station(selected_station)
            self.last_message = (True, message)
            self.enable_intent('restart_playback')

        except Exception as e:
            self.log.error("Error: {0}".format(e))
            self.log.info("Traceback: {}".format(traceback.format_exc()))
            self.speak_dialog("could.not.start.the.news.feed")

    def _play_station(self, station):
        """Play the given station using the most appropriate service."""
        # TODO convert all station references to named tuples.
        self.log.info(f'Playing News feed: {station.full_name}')
        media_url = station.media_uri
        self.log.info(f'News media url: {media_url}')
        mime = find_mime_type(media_url)
        # Ensure announcement of station has finished before playing
        wait_while_speaking()
        # If backend cannot handle https, download the file and provide a local stream.
        if media_url[:8] == 'https://' and not self.is_https_supported():
            self.download_media_file(media_url)
            self.CPS_play((f"file://{self.STREAM}", mime))
        else:
            self.CPS_play((media_url, mime))
        self.CPS_send_status(
            image=str(station.image_path),  # cast to str for json serialization
            artist=station.full_name
        )
        self.now_playing = station.full_name

    def is_https_supported(self):
        """Check if any available audioservice backend supports https"""
        for name, service in self.audioservice.available_backends().items():
            if 'https' in service['supported_uris']:
                return True
        return False

    def download_media_file(self, url):
        """Download a media file and return path to the stream"""
        # (Re)create Fifo
        if os.path.exists(self.STREAM):
            os.remove(self.STREAM)
        os.mkfifo(self.STREAM)
        self.log.debug('Running curl {}'.format(url))
        args = ['curl', '-L', quote(url, safe=":/"), '-o', self.STREAM]
        self.curl = subprocess.Popen(args)
        # Check if downloaded file is actually an error page
        if contains_html(self.STREAM):
            raise Exception('Could not fetch valid audio file.')

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


def create_skill():
    return NewsSkill()
