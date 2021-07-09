from unittest.mock import MagicMock
from bs4 import BeautifulSoup
from epicurious import *
import unittest


def as_soup(input):
    """Return a BeautifulSoup object from a response or read file

    Parameters
    ----------
    input [str or urllib3.response.HTTPResponse]

    Returns
    -------
    [bs4.BeautifulSoup]
    """
    if type(input) == str:
        # Input is a read file
        return BeautifulSoup(input, features='lxml')
    else:
        # Input is a urllib3 response
        return BeautifulSoup(input.data, features='lxml')


class TestSinglePageDownload(unittest.TestCase):
    """Download a sinlge test page
    """

    def setUp(self):
        """Set up the crawler for this one page
        """
        domain = 'www.epicurious.com'
        path = 'recipes/food/views/lemon-berry-wedding-cake-101874'
        self.url = f"https://{domain}/{path}"
        self.crawl_one = EpicuriousCrawler(
            self.url,
            f"{os.environ.get('PROJECT_PATH')}/crawler"
        )
        super().setUp()

    def tearDown(self):
        """Clear the pool manager after the test
        """
        self.crawl_one.clear_pool_manager()

    @unittest.skip('Manually run to avoid excessive downloads')
    def test_large_page(self):
        response = self.crawl_one.get_response(self.url)

        # Expect no redirects
        self.assertEqual(self.url, response.geturl())

        # Expect some page data
        self.assertIsNotNone(response.data)

        # Check a few basic html features with BeautifulSoup
        soup = as_soup(response)

        # Check title
        title_header = soup.h1
        self.assertIsNotNone(title_header)
        self.assertEqual('Lemon-Berry Wedding Cake ', title_header.get_text())

        # Check ingredient header
        ingredients_header = soup.select_one(
            'div.ingredients-info h2.section-title'
        )
        self.assertIsNotNone(ingredients_header)
        self.assertEqual('Ingredients', ingredients_header.get_text())

        # Check ingredient group count
        groups = ingredients_header.nextSibling
        self.assertIsNotNone(groups)
        group_count = len(groups.select('li.ingredient-group'))
        self.assertEqual(12, group_count)

        # Check instructions header
        instructions_header = soup.select_one(
            'div.instructions h2.section-title'
        )
        self.assertIsNotNone(instructions_header)
        self.assertEqual('Preparation', instructions_header.get_text())


class TestScrapedData(unittest.TestCase):
    """Scrape the raw data off of a single page, preserving
    the orginal presentation
    """
    def setUp(self):
        """Scrape the data off of an already downloaded page
        """
        with open('wedding_cake_test.html', 'r') as f:
            self.soup = as_soup(f.read())

        # TODO: tests to check writing to the DB
        self.conn_pool = pool.SimpleConnectionPool(1,
                                                   20,
                                                   user=os.environ.get('DB_USER'),
                                                   database=os.environ.get('DB_NAME'))
        super().setUp()

    def tearDown(self):
        """Closes the Sql Pool Manager after the test runs
        """
        self.conn_pool.closeall()

    def test_large_page(self):
        domain = 'www.epicurious.com'
        url_path = 'recipes/food/views/lemon-berry-wedding-cake-101874'
        scraper = EpicuriousScraper(self.soup,
                                    domain,
                                    url_path,
                                    '',
                                    None)

        scraper.assemble_primary()

        # Expected title
        self.assertEqual('Lemon-Berry Wedding Cake', scraper.title)

        # Expected ingredients
        # Groups appear this way on the page; might need to lump groups
        # but will need to do more QA first
        expected_ingredients = {
            'For cake': [
                '13 large eggs',
                '5 1/2 cups sugar',
                '2 2/3 cups vegetable oil',
                '2 2/3 cups part-skim ricotta cheese (about 21 ounces)',
                '1/4 cup orange juice',
                '1/4 cup grated lemon peel (from about 8 lemons)',
                '3 tablespoons orange liqueur',
                '2 1/2 tablespoons fresh lemon juice',
                '1 tablespoon vanilla extract',
                '8 3/4 cups all purpose flour',
                '2 tablespoons baking powder',
                '1 teaspoon salt'
            ],
            'For lemon filling': [
                '5 large eggs',
                '1 1/4 cups unsalted butter, room temperature',
                '1 1/4 cups sugar',
                '3/4 cup fresh lemon juice (from about 5 lemons)',
                '1 tablespoon grated lemon peel'
            ],
            'part_3': [
                '3 cups chilled whipping cream',
                '6 tablespoons sugar'
            ],
            'For lemon syrup': [
                '1 1/2 cups water',
                '3/4 cup fresh lemon juice',
                '3/4 cup sugar'
            ],
            'For preliminary assembly': [
                '1 8-inch-diameter cardboard cake round'
            ],
            'part_6': [
                '3 1/2 cups fresh raspberries, about three 6-ounce baskets',
                '3 1/2 cups fresh small blackberries or boysenberries, '
                'about three 6-ounce baskets'
            ],
            'part_7': [
                '1 12-inch-diameter cardboard cake round'
            ],
            'For frosting': [
                '11 large egg yolks',
                '3 1/4 cups plus 7 tablespoons sugar',
                '1 cup plus 2 tablespoons milk (do not use low-fat or nonfat)',
                '1 1/2 tablespoons grated lemon peel',
                '1 tablespoon vanilla extract',
                '3 pounds unsalted butter, cut into large pieces, '
                'room temperature',
                '3/4 cup water'
            ],
            'part_9': [
                '7 large egg whites'
            ],
            'For final assembly and decoration': [
                '3 12-inch-long, 1/4-inch-diameter wooden dowels'
            ],
            'part_11': [
                '1 3-foot long peach and/or cream colored ribbons',
                '2 4-foot-long peach and/or cream-colored ribbons'
            ],
            'part_12': [
                'Assorted nonpoisonous flowers (such as roses, freesias, '
                'and tulips)'
            ]
        }
        self.assertEqual(expected_ingredients, scraper.ingredients)

        # Instructions on this recipe are quite long
        # Just check the group name presence
        # and a smaller group's text
        expected_groups = [
            'Make cake:',
            'Make lemon filling:',
            'Make lemon syrup:',
            'Make preliminary assembly:',
            'Make frosting:',
            'Final assembly and decoration:',
            'To serve:'
        ]
        self.assertEqual(expected_groups, list(scraper.instructions.keys()))

        expected_syrup_instructions = [
            'Stir all ingredients in heavy medium saucepan over medium heat '
            'until sugar dissolves. Increase heat; bring to boil. Chill '
            'syrup until cold, about 1 hour. (Cakes, filling, and syrup '
            'can be made 1 day ahead. Cover cakes; store at room temperature. '
            'Cover filling and syrup; keep refrigerated.'
        ]

        self.assertEqual(expected_syrup_instructions,
                         scraper.instructions['Make lemon syrup:'])

        # Check misc
        expected_misc = {
            'servings': 'Serves 44',
            'description': "Many of the cake's components can be made a head, "
                           'and once the tiers are filled and decorated, they '
                           'can be refrigerated up to two days or frozen up '
                           "to two weeks before the wedding.\nThe rich, "
                           'lemony cake has a dense texture like that of a '
                           "pound cake.\nTo prevent discoloration of the "
                           'filling, use a saucepan with a nonreactive '
                           'interior, such as enamel or stainless steel. (The '
                           'lemon juice acid will adversely affect the '
                           "filling if it's made in an unlined iron or "
                           'aluminum saucepan.)',
            'rating': 1.0,
            'make_again': 0.94,
            'ratings': 77
        }
        self.assertEqual(expected_misc, scraper.misc)


if __name__ == '__main__':
    unittest.main()
