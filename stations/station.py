# Copyright 2021 Mycroft AI Inc.
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
"""Defines a News Station object"""

from abc import ABC, abstractproperty
from builtins import property
from pathlib import Path
from collections.abc import Callable

import feedparser

from mycroft.util import LOG


class BaseStation(ABC):
    """Abstract Base Class for all News Stations."""

    def __init__(self, acronym: str, full_name: str, image_file: str = None):
        self.acronym = acronym
        self.full_name = full_name
        self.image_file = image_file

    def as_dict(self):
        return {
            'acronym': self.acronym,
            'full_name': self.full_name,
            'image_path': str(self.image_path),
        }

    @property
    def image_path(self) -> Path:
        """The absolute path to the stations logo.

        Note that this currently traverses the path from this file and may
        break if this is moved in the file hierarchy.
        """
        if self.image_file is None:
            return None
        skill_path = Path(__file__).parent.parent.absolute()
        file_path = Path(skill_path, 'images', self.image_file)
        if not file_path.exists():
            LOG.warning(
                f'{self.image_file} could not be found, using default image')
            file_path = Path(skill_path, 'images', 'generic.png')
        return file_path

    @abstractproperty
    def media_uri(self) -> str:
        """Get the uri for the media file to be played."""
        pass


class FileStation(BaseStation):
    """News Station that provides a static url for their latest briefing."""

    def __init__(self, acronym: str, full_name: str, media_url: str, image_file: str = None):
        super().__init__(acronym, full_name, image_file)
        self._media_url = media_url

    @property
    def media_uri(self) -> str:
        """The static media url for the station."""
        return self._media_url


class FetcherStation(BaseStation):
    """News Station that requires a custom url getter function."""

    def __init__(self, acronym: str, full_name: str, url_getter: Callable, image_file: str = None):
        super().__init__(acronym, full_name, image_file)
        self._get_media_url = url_getter

    @property
    def media_uri(self) -> str:
        """Get the uri for the media file to be played.

        Uses the stations custom getter function."""
        return self._get_media_url()


class RSSStation(BaseStation):
    """News Station based on an RSS feed."""

    def __init__(self, acronym: str, full_name: str, rss_url: str, image_file: str = None):
        super().__init__(acronym, full_name, image_file)
        self._rss_url = rss_url

    @property
    def media_uri(self) -> str:
        """Get the uri for the media file to be played."""
        media_url = self.get_media_from_rss(self._rss_url)
        # TODO - check on temporary workaround and remove - see issue #87
        if self._rss_url.startswith('https://www.npr.org/'):
            media_url = media_url.split('?')[0]
        return media_url

    @staticmethod
    def get_media_from_rss(rss_url):
        try:
            data = feedparser.parse(rss_url.strip())
            # select the first link to an audio file
            for link in data['entries'][0]['links']:
                if 'audio' in link['type']:
                    media_url = link['href']
                    break
                else:
                    # fall back to using the first link in the entry
                    media_url = data['entries'][0]['links'][0]['href']
        except:
            media_url = None
        return media_url
