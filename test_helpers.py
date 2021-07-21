from bs4 import BeautifulSoup
import re


class MockRedis:
    """Mock Redis object for storing sets
    """
    # Class-level variable to store value
    sets = dict()

    def scard(self, key):
        """Count the values in a key's set

        Returns
        -------
        [int] number of items in that key's set
        """
        return len(MockRedis.sets.get(key, []))

    def sadd(self, key, value):
        """Add a value to a key's set

        Returns
        -------
        [int] 1 for successful add (ignore connection errors for now)
        """
        MockRedis.sets.setdefault(key, set())
        MockRedis.sets[key].add(value)
        return 1

    def delete(self, key):
        """Delete a key and its value set

        Returns
        -------
        [int] 1 if key was present and 0 otherwise
        """
        if key in MockRedis.sets:
            MockRedis.sets.pop(key)
            return 1
        return 0

    def sismember(self, key, value):
        """If a key's set contains a value

        Returns
        -------
        [boolean]
        """
        return key in MockRedis.sets and value in MockRedis.sets[key]

    def srem(self, key, value):
        """Remove a value from a key's set

        Returns
        -------
        [int] 1 if value was present, 0 otherwise
        """
        if self.sismember(key, value):
            MockRedis.sets[key].remove(value)
            return 1
        return 0

    def smembers(self, key):
        """Returns the set corresponding to a key
        """
        return MockRedis.sets.get(key, None)

    def srandmember(self, key):
        """Returns a value from a key's set without removing

        Returns
        -------
        [str or None]
        """
        if self.scard(key) > 0:
            for val in MockRedis.sets[key]:
                return val.encode()
        return None

    def close(self):
        """Drops the data
        """
        MockRedis.sets = dict()


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


class MockRetries:
    """Mocks the 'response.retries.redirect' call
    """
    def __init__(self):
        self.redirect = 1


def mocked_response(self, url):
    """Return a completed MockResponse for the BaseCrawler.get_response call
    """
    return MockResponse(url)


# Urls mapped to a few pages for site crawl tests
pages = {
    'https://website.com/home': 'test_site/home_page.html',
    'https://website.com/path1': 'test_site/page_1_depth_1.html',
    'https://website.com/path2': 'test_site/page_2_depth_1.html',
    'https://website.com/path3': 'test_site/page_3_depth_2.html',
    'https://image.com/the_best_image.png': 'test_site/test_image.png'
}


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
