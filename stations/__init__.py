# Copyright 2020 Mycroft AI Inc.
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
"""Define the Stations available in the News Skill."""

from mycroft.util import LOG

from .station import FetcherStation, FileStation, RSSStation, create_custom_station
from .abc import get_abc_url
from .ft import get_ft_url
from .gpb import get_gpb_url
from .tsf import get_tsf_url

# NOTE: This list has to be in sync with the settingsmeta select options.
stations = dict(
    ABC=FetcherStation('ABC', 'ABC News Australia', get_abc_url, 'ABC.png'),
    AP=RSSStation('AP', 'AP Hourly Radio News',
                  'https://www.spreaker.com/show/1401466/episodes/feed', 'AP.png'),
    BBC=RSSStation('BBC', 'BBC News',
                   'https://podcasts.files.bbci.co.uk/p02nq0gn.rss', 'BBC.png'),
    CBC=RSSStation('CBC', 'CBC News',
                   'https://www.cbc.ca/podcasting/includes/hourlynews.xml', 'CBC.png'),
    DLF=RSSStation(
        'DLF', 'DLF', 'https://www.deutschlandfunk.de/podcast-nachrichten.1257.de.podcast.xml', 'DLF.png'),
    Ekot=RSSStation(
        'Ekot', 'Ekot', 'https://api.sr.se/api/rss/pod/3795', 'Ekot.png'),
    FOX=RSSStation('FOX', 'Fox News',
                   'http://feeds.foxnewsradio.com/FoxNewsRadio', 'FOX.png'),
    FT=FetcherStation('FT', 'Financial Times', get_ft_url, 'FT.png'),
    GPB=FetcherStation('GPB', 'Georgia Public Radio', get_gpb_url, None),
    NPR=RSSStation('NPR', 'NPR News Now',
                   'https://www.npr.org/rss/podcast.php?id=500005', 'NPR.png'),
    OE3=FileStation('OE3', 'Ö3 Nachrichten',
                    'https://oe3meta.orf.at/oe3mdata/StaticAudio/Nachrichten.mp3', None),
    PBS=RSSStation('PBS', 'PBS NewsHour',
                   'https://www.pbs.org/newshour/feeds/rss/podcasts/show', 'PBS.png'),
    RDP=RSSStation('RDP', 'RDP Africa',
                   'http://www.rtp.pt//play/itunes/5442', None),
    RNE=RSSStation('RNE', 'National Spanish Radio',
                   'http://api.rtve.es/api/programas/36019/audios.rs', None),
    TSF=FetcherStation('TSF', 'TSF Radio', get_tsf_url, None),
    VRT=FileStation('VRT', 'VRT Nieuws',
                    'https://progressive-audio.lwc.vrtcdn.be/content/fixed/11_11niws-snip_hi.mp3', None),
    WDR=RSSStation(
        'WDR', 'WDR', 'https://www1.wdr.de/mediathek/audio/wdr-aktuell-news/wdr-aktuell-152.podcast', 'WDR.png'),
    YLE=RSSStation(
        'YLE', 'YLE', 'https://feeds.yle.fi/areena/v1/series/1-1440981.rss', 'Yle.png'),
)


def add_custom_station(station_url: str):
    """Create a new station from a custom url and add it to the stations list."""
    stations['custom'] = create_custom_station(station_url)