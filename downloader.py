from fake_useragent import UserAgent
from bs4 import BeautifulSoup
import requests
import re
from datetime import datetime
from urllib.parse import urlparse, unquote
import os
from humanize import naturalsize
import ujson
import sys
import utils



class Mp3Downloader:
    def __init__(self):
        ua = UserAgent()
        self.ua = ua.random
        # ua = 'Mozilla/5.0 (Windows NT 4.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/37.0.2049.0 Safari/537.36'
        accepted_content_types = ['application/octet-stream', 'audio/mpeg']
        self.headers = {'User-Agent': self.ua}

    def extract_mp3_links(self, url):
        response = requests.get(url, headers=self.headers)

        print(f'got response {response.status_code}')

        if response.status_code != 200:
            print(f'bad response. stopping')
            return []

        soup = BeautifulSoup(response.content, 'lxml')
        print(soup.title)

        #     print(soup.contents)

        mp3_links_set = set(tag['link'] for tag in soup.find_all(link=re.compile('.MP3$', re.I)))
        mp3_links_set = mp3_links_set.union(set(tag['href'] for tag in soup.find_all(href=re.compile('.MP3$', re.I))))
        mp3_links = list(mp3_links_set)

        return mp3_links

    def download_link(self, url):
        print(f'downloading {url}')
        response = requests.get(url, stream=True, headers=self.headers)
        if not (response.status_code == 200):
            print('{}: failed to download {}'.format(utils.beautiful_now(), url))
            return

        print(response.status_code)
        #     print(response.headers)

        response_headers = {key.lower(): value for key, value in response.headers.items()}

        file_names = []

        cd_header = 'content-disposition'
        if cd_header in response_headers:
            file_names += re.findall("filename=\"(.+)\"", response_headers[cd_header])

        if file_names:
            file_name = file_names[0]
        else:
            file_name = os.path.basename(unquote(urlparse(url).path))
            # file_names.append('{}-{}.mp3'.format('music', int(datetime.now().timestamp() * 1e3)))

            # print('file names:')
            # [print(f'{idx + 1} -> {name}') for idx, name in enumerate(file_names)]
            #
            # print()
            # number = int(input('give me a file name number: '))
            # file_name = file_names[number - 1]

        length = 0

        content_length_header = 'content-length'
        if content_length_header in response_headers:
            length = int(response_headers[content_length_header])

        file_name = 'downloaded_mp3s/' + file_name
        print('{}: saving to {}'.format(datetime.now(), file_name))

        downloaded = 0

        with open(file_name, 'wb') as fo:
            for chunk in response.iter_content(10240):
                fo.write(chunk)
                downloaded += len(chunk)

                percent = f'{downloaded/length*100:3.2f}% \t ' if length else ''
                sys.stdout.write(f'\r{percent}{naturalsize(downloaded)} {" "*10}')
                sys.stdout.flush()

        response.close()

        print(f'{file_name} finished!')

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

        print(f'got response {response.status_code}')

        assert (response.status_code == 200)
        # if :
        #     print(f'bad response. stopping')

        #     return []

        soup = BeautifulSoup(response.content, 'lxml')
        print(soup.title)

        a_tags = list(tag for tag in soup.find_all(href=re.compile('^\/mp3s\/mp3\/*', re.I)))

        if not a_tags:
            print('nothing found!')
            return

        print()

        results = list(
            (f"{a_tag.findNext(class_='artist_name').text} - {a_tag.findNext(class_='song_name').text}", a_tag['href']) for
            a_tag in a_tags)

        return results

        # for idx, (name, _) in enumerate(results):
        #     print(f'{idx + 1:02} - {name}')
        #
        # selected_idx = int(input('please select a result: ')) - 1
        # assert (selected_idx > 0 and selected_idx < len(results))
        #
        # selected_res = results[selected_idx]
        # self.download_radio_javan(f'https://www.radiojavan.com{selected_res[1]}')
