from unittest.mock import patch
from base_crawler import r, BaseCrawler
import unittest
import os
import re

# Urls mapped to a few pages for a site crawl tests
pages = {
    'https://website.com/home': 'test_site/home_page.html',
    'https://website.com/path1': 'test_site/page_1_depth_1.html',
    'https://website.com/path2': 'test_site/page_2_depth_1.html',
    'https://website.com/path3': 'test_site/page_3_depth_2.html',
    'https://image.com/the_best_image.png': 'test_site/test_image.png'
}


class MockRetries:
    """Mocks the 'response.retries.redirect' call
    """
    def __init__(self):
        self.redirect = 1


class MockResponse:
    """Mocks the response object calls within BaseCrawler
    """
    def __init__(self, url):
        """Methods and attributes to stub a urllib3 response object
        """
        self.url = url
        self.status = 200
        self.data = self.load_mock_page()
        self.retries = MockRetries()

    def load_mock_page(self):
        """Get the file corresponding to its url and load
        """
        to_read = pages[self.url]

        with open(to_read, 'rb') as f:
            return f.read()

    def get_url(self):
        """Returns the url
        """
        return self.url


def mocked_response(self, url):
    """Return a completed MockResponse for the BaseCrawler.get_response call
    """
    return MockResponse(url)


def recipe_page_element(soup):
    """An example function that would be defined in a specific site's
    scraper for sites whose urls are not enough to determine if a page
    is a recipe or not

    Since this could potentially be iterating over siblings to find an element
    I felt defining a full function rather than passing a css string to
    the crawler could be beneficial

    These functions should still be quite basic, though

    Paremeters
    ----------
    soup [bs4.BeautifulSoup]: the full html of a page

    Returns
    -------
    [bs4.element.tag]: presence (or lack) of the desired element
    """
    # The 2 recipe pages are marked by their '<h2 id="recipe-page">
    # elements containing 'Ingredients' text
    return soup.find('h2',
                     id='recipe-page',
                     text=re.compile(r"^\s*Ingredients\s*$", flags=re.I))


# Mock a few method calls and skip sleep/print statements
@patch.object(BaseCrawler, 'get_response', mocked_response)
@patch.object(BaseCrawler, 'download_page', return_value=None)
@patch.object(BaseCrawler, 'setup_pool_manager_headers', return_value=None)
@patch('base_crawler.sleep', return_value=None)
@patch('base_crawler.print', return_value=None)
class TestSiteCrawl(unittest.TestCase):
    """Crawl a small (mock) site of 4 pages
    Layout will look like:
    - home_page
      - page_1_depth_1
      - page_2_depth_1
        - page_3_depth_2
    """
    def setUp(self):
        """Set up the crawler for this one page
        """
        domain = 'website.com'
        path = 'home'
        self.url = f"https://{domain}/{path}"
        self.crawl = BaseCrawler(
            self.url,
            f"{os.environ.get('PROJECT_PATH')}/crawler"
        )

        # Remove the 'downloaded' image if already present
        if os.path.os.path.isfile('home.png'):
            os.remove('home.png')

        super().setUp()

    def tearDown(self):
        """Clear the pool manager after the test
        """
        # Remove any Redis keys
        r.delete(self.crawl.rkey(0))
        r.delete(self.crawl.rkey(1))
        r.delete(self.crawl.rkey(2))
        r.delete(self.crawl.rkey(3))
        r.close()

        # Remove the 'downloaded' image
        if os.path.os.path.isfile('home.png'):
            os.remove('home.png')

    def test_site_crawl(self, *args):
        """Test crawling the full site
        """
        # Expect no 'finished' pages before starting
        finished_count = r.scard(self.crawl.rkey(1))
        self.assertEqual(0, finished_count)

        # Crawl the site
        self.crawl.crawl_domain()

        # Expect 4 'finished' pages once completed
        finished_count = r.scard(self.crawl.rkey(1))
        self.assertEqual(4, finished_count)

    def test_avoiding_urls(self, *args):
        """Test crawling the site while avoiding links with specific
        path patterns
        """
        # Expect no 'finished' pages before starting
        finished_count = r.scard(self.crawl.rkey(1))
        self.assertEqual(0, finished_count)

        # Crawl the site
        # Update the crawl to avoid 'path2', resulting in 2 fewer pages
        # as it won't visit that page along with the link on it
        self.crawl.avoid = ['path2']
        self.crawl.crawl_domain()

        # Expect 2 'finished' pages once completed
        finished_count = r.scard(self.crawl.rkey(1))
        self.assertEqual(2, finished_count)

    def test_scrapable_page_by_url(self, *args):
        """Test crawling the site and handling scrapable pages
        and their images by a provided url path pattern
        """
        # Pretend only the first page is scrapable
        # Mark scrapable pages' image location
        self.crawl.image_css = 'div.my-image img'
        self.crawl.image_att = 'src'
        # Regex pattern showing that paths containing 'home' are scrapable
        self.crawl.path_pattern = r"home"
        # Avoid any links containing 'path'
        self.crawl.avoid = ['path']

        # Expect no 'finished' pages before starting
        finished_count = r.scard(self.crawl.rkey(1))
        self.assertEqual(0, finished_count)

        # Expect no 'to_scrape' pages before starting
        to_scrape_count = r.scard(self.crawl.rkey(3))
        self.assertEqual(0, to_scrape_count)

        # Expect no image to have been collected yet
        self.assertFalse(os.path.isfile('home.png'))

        # Crawl the site
        self.crawl.crawl_domain()

        # Expect 1 'to_scrape' page after crawling
        to_scrape_count = r.scard(self.crawl.rkey(3))
        self.assertEqual(1, to_scrape_count)

        # An image should have been downloaded on the scrapable home page
        self.assertTrue(os.path.isfile('home.png'))

        # Expect no 'finished' pages as the 1 is in 'to_scrape'
        finished_count = r.scard(self.crawl.rkey(1))
        self.assertEqual(0, finished_count)

    def test_scrapable_page_by_element(self, *args):
        """Test crawling the site and handling scrapable pages
        using a element presence check function
        """
        self.crawl.html_function = recipe_page_element
        # Expect no 'finished' pages before starting
        finished_count = r.scard(self.crawl.rkey(1))
        self.assertEqual(0, finished_count)

        # Expect no 'to_scrape' pages before starting
        to_scrape_count = r.scard(self.crawl.rkey(3))
        self.assertEqual(0, to_scrape_count)

        # Crawl the site
        self.crawl.crawl_domain()
        # Expect 2 'to_scrape' page after crawling
        to_scrape_count = r.scard(self.crawl.rkey(3))
        self.assertEqual(2, to_scrape_count)

        # Expect 2 'finished' pages as the other 2 are in 'to_scrape'
        finished_count = r.scard(self.crawl.rkey(1))
        self.assertEqual(2, finished_count)


if __name__ == '__main__':
    unittest.main()
