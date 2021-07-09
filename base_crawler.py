from urllib3 import PoolManager, Timeout, Retry
from urllib3.exceptions import HTTPError
from urllib3.util import parse_url
from bs4 import BeautifulSoup
from redis import Redis
from time import sleep
from helpers import *
import requests
import certifi
import json
import os
import re

# Open the Redis connection:
r = Redis()


class BaseCrawler():
    def __init__(self, start_url, download_path, **kwargs):
        """Crawl links within a domain. Unseen urls are added to a Redis set,
        feeding the crawler.

        Parameters
        ----------
        start_url [str]: starting point (NOTE: change to list?)
        download_path [str]: directory to download page html
        allow [list[str]]: elements a link path MUST contain in order to crawl
        avoid [list[str]]: elements a link path CANNOT contain
            (overrules allow)
        ignore_links bool]: only download the in_progress urls, without
            looking for more links
        limit [int]: total pages to download before stopping
        image_css [str]: css path to a recipe's image
        """
        # Ensure the download path exists
        if not os.path.isdir(download_path):
            raise Exception('Non-existent download path')

        # Set up self.start_url, self.scheme, self.domain, and self.path
        self.prepare_url(start_url)
        if not self.domain:
            raise Exception('Invalid starting url')

        self.download_path = download_path

        self.allow = kwargs.get('allow', [])
        self.avoid = kwargs.get('avoid', [])
        self.find_more_links = kwargs.get('find_more_links', True)
        self.limit = kwargs.get('limit', 1000)
        self.page_count = 0
        self.setup_pool_manager_headers()

    def prepare_url(self, url):
        """Set up url-related attributes for the crawler

        Parameters
        ----------
        url [str]: full url
        """
        self.start_url = url

        scheme, domain, path = self.url_parts(url)
        self.base_url = f"{scheme}://{domain}"
        self.scheme = scheme
        self.domain = domain
        self.path = path

    def url_parts(self, url):
        """
        Pull out the scheme, domain, and full path of a url

        Parameters
        ----------
        url [str]: either a full url or a path only

        Returns
        -------
        scheme [str]: scheme of the url; can be None
        domain [str]: domain of the url
        path   [str]: full path (including query/fragment); can be None
        """
        url_reg = r"""
            (?:(?P<scheme>https?)://)?
            (?P<host>(?:www\.)?[^/]+\.[^/]+)
            (?P<path>/.+)
        """
        match = re.search(url_reg, url, flags=re.I | re.X)
        # If no match, assume the provided url is just a relative path
        if not match:
            if not url.startswith('/'):
                url = '/' + url
            return (None, None, url)
        return match.groups()

    def setup_pool_manager_headers(self):
        """Setup the urllib3 Pool Manager and headers
        as class parameters to access within `get_response` below
        """
        self.http = PoolManager(cert_reqs='CERT_REQUIRED',
                                ca_certs=certifi.where())
        self.headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,'
                      'image/avif,image/webp,image/apng,*/*;q=0.8,'
                      'application/signed-exchange;v=b3;q=0.9',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 11_2_0) '
                          'AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/89.0.4389.90 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9'
        }

    def clear_pool_manager(self):
        """Closes the urllib3 Pool Manager
        """
        self.http.clear()

    def get_response(self, url):
        """Download a single page using the urllib3 library
        - Allow 2 additional tries
        - At most a single redirect (on the same host)
        - 10 seconds to connect and read

        Parameters
        ----------
        url [str]: the full url to request

        Returns
        -------
        response [urllib3.response.HTTPResponse]: response object
        """
        return self.http.request('GET',
                                 url,
                                 headers=self.headers,
                                 timeout=Timeout(connect=10.0, read=10.0),
                                 retries=Retry(3,
                                               redirect=1,
                                               raise_on_redirect=False),
                                 assert_same_host=True)

    def crawl_domain(self):
        """Kicks of the crawling of a domain.
        Find links on each pages and add to Redis.
        Links must be the same host and optionally may have path restrictions.

        Finish once the "in_progress" set in Redis is empty
        """
        # Check if a crawl is in progress;
        # add the start_url path if not
        if r.scard(self.rkey(0)) == 0:
            r.sadd(self.rkey(0), self.path)
        while r.scard(self.rkey(0)) > 0:
            # Every 10 pages, count the number of in progress records
            if self.page_count % 10 == 0:
                r.rpush(self.rkey(3), r.scard(self.rkey(0)))

            next_path = r.srandmember(self.rkey(0)).decode()
            current_url = f"{self.base_url}{next_path}"

            try:
                response = self.get_response(current_url)
                # Check if a single redirection occurred
                if response.retries.redirect == 0:
                    next_path = self.handle_redirection(next_path, response)
                print(response.status)
                html = response.data
            except Exception as e:
                # Add the url to the errored set and remove from in_progress
                self.log_crawler_error(next_path, e)
                # Still print to console along with logging above
                print(f"\n{e.__class__.__name__}: {e.args}: {current_url}\n")
                r.sadd(self.rkey(2), next_path)
                r.srem(self.rkey(0), next_path)
                self.page_count += 1
                continue

            soup = BeautifulSoup(html, features='lxml')
            if self.find_more_links:
                self.add_links(soup)
            self.download_page(html, next_path)
            self.complete_page(next_path)
            print(f"Completed download of {next_path}")

            if self.page_count >= self.limit:
                r.srem(self.rkey(0), next_path)
                break

            # Slow things down
            sleep(1)

    def handle_redirection(self, old_path, response):
        """Remove the old path from 'in_progress' and add to 'finished'
        while adding the new path to 'in_progress'

        Parameters
        ----------
        old_path [str]: the original path requested
        response [urllib3.response.HTTPResponse]: redirected response object

        Returns
        -------
        new_path [str]: the path of the newly redirected page
        """
        _, _, new_path = self.url_parts(response.geturl())
        if not new_path:
            # This has never happend but just in case
            raise Exception('Missing redirected URL')
        # Remove the old path from in_progess and add to finished
        r.srem(self.rkey(0), old_path)
        r.sadd(self.rkey(1), old_path)
        # Add the new one to in_progress
        r.sadd(self.rkey(0), new_path)

        return new_path

    def add_links(self, soup):
        """If links are found (matching provided allowed or in general),
        add them to the urls to crawl if:
        - not hidden
        - on the same domain as the starting url
        - contain any provided restrictions
        - haven't been previously seen

        Parameters
        ----------
        soup [bs4.BeautifulSoup]: the current page to parse for links

        Returns
        -------
        None; simply adds links to the 'in_progress' set
        """
        for link in self.page_links(soup):
            # TODO: more elegant way of handling this?
            if 'hidden' in str(link).lower() and \
               'overflow-hidden' not in str(link).lower():
                continue
            # Get a proper path
            link_url = link.get('href')
            if not link_url:
                continue
            link_domain, link_path = self.url_from_href(link_url)
            if self.skip_link(link_domain, link_path):
                continue
            # Url is on the current domain and hasn't
            # been visited; add to the set to crawl
            r.sadd(self.rkey(0), link_path)

    def page_links(self, soup):
        """Gather every link on the page. If 'allow' is provided, ensure each
        is found within href. Regardless ensure each link contains text

        Parameters
        ----------
        see `add_links` above

        Returns
        -------
        links [list[str]]: links to be added to the 'in_progess' set
        """
        if self.allow:
            links = []
            for substring in self.allow:
                links.extend(
                    soup.find_all('a',
                                  href=lambda href: substring in str(href))
                )
            return links
        else:
            return soup.find_all('a', href=True, text=True)

    def url_from_href(self, href_url):
        """
        Handles the href pulled out of link elements
        Path is used for Redis keys and downloaded filenames

        Parameters
        ----------
        domain   [str]: domain of the site being crawled
        href_url [str]: href attribute of a link element

        Returns
        -------
        domain [str]: domain pulled from the href, if any
        path   [str]: full path from the href
        """

        if href_url.startswith('//'):
            # TODO: separate file for constants like this
            url_reg = r"""//
                (?P<domain>[^/]{3,})
                (?P<path>/.*)
            """
            match = re.search(url_reg, href_url, flags=re.I | re.X)
            if not match:
                raise Exception(f"Scary path: {href_url}")
            return match.groups()
        elif href_url.startswith('/../'):
            return None, href_url[3:]
        elif href_url.startswith('/'):
            return None, href_url
        else:
            # See if the domain is included;
            # otherwise return the full path
            _, domain, path = self.url_parts(href_url)
            return domain, path

    def skip_link(self, link_domain, link_path):
        """Skip a found link if:
        - too long
        - external domain
        - already 'finished' or 'errored'
        - marked to avoid
        - potentially messy like 'htt' within the path

        Parameters
        ----------
        link_domain [str]: check versus domain being crawled
        link_path [str]: path to check

        Returns
        -------
        boolean: whether to include or ignore the given link
        """
        return not link_path or\
            len(link_path) > 120 or\
            not self.same_domains(link_domain) or\
            r.sismember(self.rkey(1), link_path) or\
            r.sismember(self.rkey(2), link_path) or\
            self.avoid_link(link_path) or\
            self.messy_path(link_path)

    def messy_path(self, link_path):
        """
        Check for general messiness
        """
        return 'http' in link_path

    def avoid_link(self, link_path):
        """Check for substrings to avoid

        Parameters
        ----------
        link_path [str]: substring of a link; avoid if found
        """
        if not self.avoid:
            return False
        for substring in self.avoid:
            if substring in link_path:
                return True
        return False

    def same_domains(self, domain):
        """
        Quick check to ensure a crawl remains on one domain

        Parameters
        ----------
        domain [str]: domain to compare against self.domain
        """
        return not domain or\
            (self.domain.lstrip('www.').rstrip('/') ==
             domain.lstrip('www.').rstrip('/'))

    def download_page(self, html, path):
        """Saves a local copy of the raw html to process later

        Parameters
        ----------
        html [str]: result of response.data; html of the current page
        path [str]: path of the current page; used as file name
        """
        file_name = path.lstrip('/').replace('/', '_-_')
        with open(f'{self.download_path}/{file_name}.html', 'w') as f:
            if type(html) == bytes:
                f.write(html.decode())
            else:
                f.write(html)

    def download_image(self, image_url, file_name):
        """Download a recipe's image if image_css is provided
        Keep the file name the same as the recipe path and write
        as the same image type as listed on the url

        Parameters
        ----------
        image_url [str]: url pulled out of an 'src' or 'srcset' attribute
        file_name [str]: derived from the path of the recipe
        """
        file_type = image_url.split('.')[-1]
        img = self.get_response(image_url)

        with open(f'{self.download_path}/{file_name}.{file_type}', 'wb') as f:
            f.write(img.data)

    def complete_page(self, next_path):
        """Increment the page count, add the current path to the
        success set, and remove it from the in progress set
        """
        self.page_count += 1
        r.sadd(self.rkey(1), next_path)
        r.srem(self.rkey(0), next_path)

    def log_crawler_error(self, path, error, note=None):
        """Write errors to a file for later viewing
        Json lines format for easy reading into Pandas later on
        """
        error_dict = {
            'path': path,
            'error_type': error.__class__.__name__,
            'error_message': error.args
        }
        # Optional additional note
        if note:
            error_dict['note'] = note

        with open(f"{self.download_path}/crawler_errors.jsonl", 'a') as f:
            f.write(json.dumps(error_dict) + "\n")

    def rkey(self, part_index):
        """Redis key: combine domain with 'in_progress', 'finished',
        or 'errored'
        """
        parts = ['in_progress', 'finished', 'errored', 'count']
        return f"{self.domain}:{parts[part_index]}"
