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

import pytz
import requests
from datetime import datetime

def get_url():
    """Custom news fetcher for ABC News Australia briefing"""
    # Format template with (hour, day, month)
    url_temp = ('https://abcmedia.akamaized.net/news/audio/news-briefings/'
                'top-stories/{}{}/NAUs_{}00flash_{}{}_nola.mp3')
    now = pytz.utc.localize(datetime.utcnow())
    syd_tz = pytz.timezone('Australia/Sydney')
    syd_dt = now.astimezone(syd_tz)
    hour = syd_dt.strftime('%H')
    day = syd_dt.strftime('%d')
    month = syd_dt.strftime('%m')
    year = syd_dt.strftime('%Y')
    url = url_temp.format(year, month, hour, day, month)

    # If this hours news is unavailable try the hour before
    response = requests.get(url)
    if response.status_code != 200:
        hour = str(int(hour) - 1)
        url = url_temp.format(hour, day, month)

    return url
