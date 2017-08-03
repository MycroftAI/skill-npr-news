# Copyright 2016 Mycroft AI, Inc.
#
# This file is part of Mycroft Core.
#
# Mycroft Core is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Mycroft Core is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Mycroft Core.  If not, see <http://www.gnu.org/licenses/>.


import feedparser
import time
from os.path import dirname
import re

from adapt.intent import IntentBuilder
from mycroft.skills.core import MycroftSkill
from mycroft.util.log import getLogger
try:
    from mycroft.skills.audioservice import AudioService
except:
    from mycroft.util import play_mp3
    AudioService = None

__author__ = 'jdorleans'

LOGGER = getLogger(__name__)


class NPRNewsSkill(MycroftSkill):
    def __init__(self):
        super(NPRNewsSkill, self).__init__(name="NPRNewsSkill")
        self.url_rss = self.config['url_rss']
        self.process = None
        self.audioservice = None

    def initialize(self):
        intent = IntentBuilder("NPRNewsIntent").require(
            "NPRNewsKeyword").build()
        self.register_intent(intent, self.handle_intent)

        intent = IntentBuilder("NPRNewsStopIntent") \
                .require("NPRNewsStopVerb") \
                .require("NPRNewsKeyword").build()
        self.register_intent(intent, self.handle_stop)

        if AudioService:
            self.audioservice = AudioService(self.emitter)

    def handle_intent(self, message):
        try:
            data = feedparser.parse(self.url_rss)
            self.stop()

            self.speak_dialog('npr.news')

            # Pause for the intro, then start the new stream
            time.sleep(4)
            url = re.sub('https', 'http',
                         data['entries'][0]['links'][0]['href'])
            # if audio service module is available use it
            if self.audioservice:
                self.audioservice.play(url, message.data['utterance'])
            else: # othervice use normal mp3 playback
                self.process = play_mp3(url)

        except Exception as e:
            LOGGER.error("Error: {0}".format(e))

    def handle_stop(self, message):
        self.stop()

    def stop(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()
            self.process.wait()
            self.speak_dialog('npr.news.stop')


def create_skill():
    return NPRNewsSkill()
