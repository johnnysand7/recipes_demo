from unittest.mock import patch
from test_helpers import *
from base_crawler import *
import unittest


# Mock a few crawler methods involving any connections/page download
@patch.object(BaseCrawler, 'get_response', mocked_response)
@patch.object(BaseCrawler, 'download_page', return_value=None)
@patch.object(BaseCrawler, 'setup_pool_manager_headers', return_value=None)
# Mock a Redis store
@patch('base_crawler.r', new_callable=MockRedis)
# Mock sleep/print statements for speed/cleanliness
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
        """Remove any test image if present
        """
        # Drops anything in the MockRedis object
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
    r = MockRedis()
    unittest.main()
