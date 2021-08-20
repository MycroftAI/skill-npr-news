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
from urllib.parse import quote

from adapt.intent import IntentBuilder
from mycroft.audio import wait_while_speaking
from mycroft.skills.core import intent_handler, intent_file_handler
from mycroft.skills.common_play_skill import CommonPlaySkill, CPSMatchLevel
from mycroft.util import get_cache_directory

from .stations import set_custom_station, stations
from .stations.match import match_station_from_utterance, Match
from .stations.util import contains_html, find_mime_type


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
        self.settings_change_callback = self.on_websettings_changed
        self.on_websettings_changed()

    def on_websettings_changed(self):
        """Callback triggered anytime Skill settings are modified on backend."""
        station_code = self.settings.get("station", "not_set")
        custom_url = self.settings.get("custom_url")
        if station_code == "not_set" and len(custom_url) > 0:
            self.log.info("Creating custom News Station from Skill settings.")
            set_custom_station(custom_url)
        
    def CPS_start(self, phrase, data):
        if data and data.get('acronym'):
            # Play the requested news service
            station = stations[data['acronym']]
        else:
            # Just use the default news feed
            station = None
        self.handle_play_request(station=station)
        

    def CPS_match_query_phrase(self, phrase):
        """Respond to Common Play Service query requests."""
        match = match_station_from_utterance(self, phrase)
        
        # If no match but utterance contains news, return low confidence level
        if match.confidence < CONF_GENERIC_MATCH and self.voc_match(phrase, "News"):
            match = Match(self.get_default_station(), CONF_GENERIC_MATCH)

        # Translate match confidence levels to CPSMatchLevels
        if match.confidence >= CONF_EXACT_MATCH:
            match_level = CPSMatchLevel.EXACT
        elif match.confidence >= CONF_LIKELY_MATCH:
            match_level = CPSMatchLevel.ARTIST
        elif match.confidence >= CONF_GENERIC_MATCH:
            match_level = CPSMatchLevel.CATEGORY
        else:
            return None
            
        return (match.station.full_name, match_level, match.station.as_dict())

    def get_default_station(self):
        """Get default station for user.

        Fallback order:
        1. Station defined in Skill Settings
        2. Default station for country
        3. NPR News as global default
        """
        station = None
        station_code = self.settings.get('station', 'not_set')
        custom_url = self.settings.get('custom_url', '')
        if station_code != 'not_set':
            station = stations[station_code]
        elif len(custom_url) > 0:
            station = stations.get('custom')
        if station is None:
            station = self.get_default_station_by_country()
        if station is None:
            station = stations['NPR']
        return station

    def get_default_station_by_country(self):
        """Get the default station based on the devices location."""
        country_code = self.location['city']['state']['country']['code']
        station_code = self.default_feed.get(country_code)
        return stations.get(station_code)

    @intent_file_handler("PlayTheNews.intent")
    def handle_latest_news_alt(self, message):
        # Capture some alternative ways of requesting the news via Padatious
        match = match_station_from_utterance(self, message.data["utterance"])
        if match and len(match) > 2:
            station_dict = match[2]
            station = stations[station_dict['acronym']]
        else:
            station = self.get_default_station()

        self.handle_play_request(message, station)

    @intent_handler(IntentBuilder("").one_of("Give", "Latest").require("News"))
    def handle_latest_news(self, message):
        match = match_station_from_utterance(self, message.data['utterance'])
        if match:
            selected_station = match.station
        else:
            selected_station = self.get_default_station()
        self.handle_play_request(message, selected_station)

    def handle_play_request(self, message=None, station=None):
        """Handle request to play a station."""
        self.stop()
        # Speak intro while downloading in background
        self.speak_dialog('news', data={"from": station.full_name})
        self._play_station(station)
        self.last_message = (True, message)
        self.enable_intent('restart_playback')

    def _play_station(self, station):
        """Play the given station using the most appropriate service."""
        try:
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
                # cast to str for json serialization
                image=str(station.image_path),
                artist=station.full_name
            )
            self.now_playing = station.full_name
        except Exception as e:
            self.speak_dialog("could.not.start.the.news.feed")
            self.log.exception(e)

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
        self.now_playing = None
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
