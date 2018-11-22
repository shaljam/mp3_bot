import os
import re
import ujson
from datetime import datetime
from urllib.parse import urlparse, unquote

import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

import utils


class Mp3Downloader:
    def __init__(self):
        ua = UserAgent()
        self.ua = ua.random
        self.headers = {'User-Agent': self.ua}

    def download_link(self, url):
        print(f'downloading {url}')
        response = requests.get(url, stream=True, headers=self.headers)
        if not (response.status_code == 200):
            print('{}: failed to download {}'.format(utils.beautiful_now(), url))
            return

        response_headers = {key.lower(): value for key, value in response.headers.items()}

        file_names = []

        cd_header = 'content-disposition'
        if cd_header in response_headers:
            file_names += re.findall("filename=\"(.+)\"", response_headers[cd_header])

        if file_names:
            file_name = file_names[0]
        else:
            file_name = os.path.basename(unquote(urlparse(url).path))

        length = 0

        content_length_header = 'content-length'
        if content_length_header in response_headers:
            length = int(response_headers[content_length_header])

        file_name = 'downloaded_mp3s/' + file_name
        print('{}: saving to {}'.format(datetime.now(), file_name))

        downloaded = 0

        with open(file_name, 'wb') as fo:
            for chunk in response.iter_content(20480):
                fo.write(chunk)
                downloaded += len(chunk)

        response.close()

        print(f'{file_name} downloaded!')

        return file_name

    def download_radio_javan(self, url):

        if not url.startswith('https://www.radiojavan.com'):
            url = f'https://www.radiojavan.com{url}'

        if 'podcast' in url:
            print('this is a podcast!')
            mp3_podcast = 'podcast'
        else:
            mp3_podcast = 'mp3'

        rj_id = os.path.basename(unquote(urlparse(url).path))
        rj_gethost_url = f'https://www.radiojavan.com/{mp3_podcast}s/{mp3_podcast}_host'

        response = requests.post(rj_gethost_url, data={'id': rj_id}, headers=self.headers)

        print(f'got response {response.status_code}')

        if response.status_code != 200:
            print(f'bad response. stopping')
            return

        print(response.content)

        js = ujson.loads(response.content)

        if not 'host' in js:
            return

        rj_host = js['host']

        print(rj_host)

        rj_url_path = f'media/{mp3_podcast}/mp3-192'

        mp3_url = f'{rj_host}/{rj_url_path}/{rj_id}.mp3'

        return self.download_link(mp3_url)

    def search_rj(self, query):
        url = f'https://www.radiojavan.com/search?query={query}&type=mp3'

        response = requests.get(url, headers=self.headers)

        if response.status_code != 200:
            print(f'bad response {url} {response.status_code}')
            return []

        soup = BeautifulSoup(response.content, 'lxml')

        a_tags = list(tag for tag in soup.find_all(href=re.compile('^\/mp3s\/mp3\/*', re.I)))

        if not a_tags:
            print('nothing found!')
            return []

        results = list(
            (f"{a_tag.findNext(class_='artist_name').text} - {a_tag.findNext(class_='song_name').text}", a_tag['href']) for
            a_tag in a_tags)

        return results
