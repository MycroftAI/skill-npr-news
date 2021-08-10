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

from urllib.request import urlopen

from bs4 import BeautifulSoup

def abc():
    """Custom news fetcher for ABC News Australia briefing"""
    domain = "https://www.abc.net.au"
    latest_briefings_url = f"{domain}/radio/newsradio/news-briefings/"
    soup = BeautifulSoup(urlopen(latest_briefings_url), features='html.parser')
    result = soup.find(id="collection-grid3")
    episode_page_link = result.find_all('a')[0]['href']
    episode_page = urlopen(domain + episode_page_link)
    episode_soup = BeautifulSoup(episode_page, features='html.parser')
    mp3_url = episode_soup.find_all(attrs={"data-component": "DownloadButton"})[0]['href']
    return mp3_url
