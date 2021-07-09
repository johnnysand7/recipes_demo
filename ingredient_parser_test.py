from ingredient_parser import *
from recipe_constants import *
from unittest.mock import MagicMock
import unittest


def return_details(ingredient, table_rows=[]):
    """Returns the details hash of the IngredientParser object.
    Most tests will ignore the lookup, so mock out.
    """
    parser = IngredientParser(ingredient)
    parser.lookup = MagicMock(return_value=table_rows)
    return parser.parse()


def test_parsing(ingredient, **kwargs):
    expected_cleaned = kwargs.get('cleaned')
    expected_volume = kwargs.get('volume')
    expected_weight = kwargs.get('weight')

    details = return_details(ingredient)
    if expected_cleaned:
        self.assertEqual(details['cleaned'], expected_cleaned)
    if expected_volume:
        self.assertEqual(details['volume'], expected_volume)
    if expected_weight:
        self.assertEqual(details['weight'], expected_weight)


class TestStringCleaning(unittest.TestCase):
    """Tests for cleaning strings"""

    def test_accent_removal(self):
        cleaned = IngredientParser('jalapeño').cleaned
        self.assertEqual(cleaned, 'jalapeno')

    def test_remove_dimensions(self):
        test_string = '1 3x1" strip of lemon peel'
        cleaned = IngredientParser(test_string).cleaned
        self.assertEqual(cleaned, '1  strip of lemon peel')

        test_string = '8 1/2-inch-thick slices country white bread'
        cleaned = IngredientParser(test_string).cleaned
        self.assertEqual(cleaned, '8   slices country white bread')

    def test_remove_plural(self):
        cleaned = standardize_ending('strawberries')
        self.assertEqual(cleaned, 'strawberry')

        cleaned = standardize_ending('cookies')
        self.assertEqual(cleaned, 'cookie')

        cleaned = standardize_ending('tomatoe')
        self.assertEqual(cleaned, 'tomato')

        cleaned = standardize_ending('peaches')
        self.assertEqual(cleaned, 'peach')

        cleaned = standardize_ending('octopuses')
        self.assertEqual(cleaned, 'octopus')

        # Molasses is the only word in the entire dataset where dropping
        # '-es' is incorrect
        cleaned = standardize_ending('molasses')
        self.assertEqual(cleaned, 'molass')

    def test_remove_percentages(self):
        cleaned = remove_percentage('3cups 2-percent milk')
        self.assertEqual(cleaned, '3cups milk')

        cleaned = remove_percentage('3cups 2% milk')
        self.assertEqual(cleaned, '3cups milk')

    def test_and(self):
        cleaned = standardize_characters('mac n cheese')
        self.assertEqual(cleaned, 'mac and cheese')

        cleaned = standardize_characters('mac&cheese')
        self.assertEqual(cleaned, 'mac and cheese')

        cleaned = standardize_characters('mac-and-cheese')
        self.assertEqual(cleaned, 'mac and cheese')


class TestVolumeConversion(unittest.TestCase):
    """Tests for converting volumes.
    All found volumes converted to cups.
    """
    # 100 milliliter == 0.4227 cups
    def test_ml(self):
        volume = return_details('100ml of milk')['volume']
        self.assertEqual(volume, 0.4227)

        volume = return_details('100 milliliters of milk')['volume']
        self.assertEqual(volume, 0.4227)

    # 3 teaspoons == 0.0625 cups
    def test_tsp(self):
        test_string = '3 tspn of sugar'
        volume = return_details(test_string)['volume']
        self.assertEqual(volume, 0.0625)

    # 1 tablespoon == 0.0625 cups
    def test_tbsp(self):
        test_string = '1 table spoon sugar'
        volume = return_details(test_string)['volume']
        self.assertEqual(volume, 0.0625)

        test_string = '1 tbsp sugar'
        volume = return_details(test_string)['volume']
        self.assertEqual(volume, 0.0625)

    # Assuming 1 spoonful == 1 tablespoon
    def test_spoonful(self):
        test_string = '1 spoonful sugar'
        volume = return_details(test_string)['volume']
        self.assertEqual(volume, 0.0625)

    # 1 fluid ounce == 0.125 cups
    def test_fluid_ounce(self):
        test_string = '1 fluid oz milk'
        volume = return_details(test_string)['volume']
        self.assertEqual(volume, 0.125)

    # 1 cup == 1 cup
    def test_cups(self):
        test_string = '1 cup of milk'
        volumes = return_details(test_string)['volume']
        self.assertEqual(volume, 1.0)

        test_string = '1C of milk'
        volumes = return_details(test_string)['volume']
        self.assertEqual(volume, 1.0)

    # 1 pint == 2 cups
    def test_cups(self):
        test_string = '1 pint of milk'
        volume = return_details(test_string)['volume']
        self.assertEqual(volume, 2.0)

    # 1 quart == 4 cups
    def test_quarts(self):
        test_string = '1 qt of milk'
        volume = return_details(test_string)['volume']
        self.assertEqual(volume, 4.0)

    # 1 liter == 4.2268 cups
    def test_liters(self):
        test_string = '1L of milk'
        volume = return_details(test_string)['volume']
        self.assertEqual(volume, 4.2268)

        test_string = '1 liter of milk'
        volume = return_details(test_string)['volume']
        self.assertEqual(volume, 4.2268)

    # 1 gallon == 16 cups
    def test_gallons(self):
        test_string = '1 gallon of milk'
        volume = return_details(test_string)['volume']
        self.assertEqual(volume, 16.0)


class TestWeightConversion(unittest.TestCase):
    """Tests for converting weights.
    All found weights converted to grams.
    """
    # 1 gram == 1 gram
    def test_grams(self):
        test_string = '1 gram of sugar'
        weight = return_details(test_string)['weight']
        self.assertEqual(weight, 1.0)

        test_string = '1g. sugar'
        weight = return_details(test_string)['weight']
        self.assertEqual(weight, 1.0)

    # 1 ounce == 28.34 grams
    def test_ounces(self):
        test_string = '1 ounce of butter'
        weight = return_details(test_string)['weight']
        self.assertEqual(weight, 28.34)

        test_string = '1oz. of butter'
        weight = return_details(test_string)['weight']
        self.assertEqual(weight, 28.34)

    # 1 stick of butter == 113.4 grams
    def test_sticks_butter(self):
        test_string = '1 stick of butter'
        weight = return_details(test_string)['weight']
        self.assertEqual(weight, 113.4)

    # 1 pound == 453.59 grams
    def test_pounds(self):
        test_string = '1 pound of butter'
        weight = return_details(test_string)['weight']
        self.assertEqual(weight, 453.59)

        test_string = '1 lb of butter'
        weight = return_details(test_string)['weight']
        self.assertEqual(weight, 453.59)

    # 1 kilogram == 1000 grams
    def test_pounds(self):
        test_string = '1 kg of butter'
        weight = return_details(test_string)['weight']
        self.assertEqual(weight, 1000)

        test_string = '1 kilo of butter'
        weight = return_details(test_string)['weight']
        self.assertEqual(weight, 1000)

        test_string = '1kilo gram of butter'
        weight = return_details(test_string)['weight']
        self.assertEqual(weight, 1000)


class TestSpelledNumber(unittest.TestCase):
    """Tests for spelling out numbers/fractions to decimals.
    Variants are:
    - spelled out integers
    - spelled out fractions
    - numerator/denominator fractions
    - fraction characters
    """
    def test_spelled_integers_1(self):
        test_string = 'Two or three cups milk'
        output = return_details(test_string)
        self.assertEqual(output['volume'], 2.5)

    def test_spelled_integers_2(self):
        test_string = 'A spoonful or two of sesame seeds'
        output = return_details(test_string)
        self.assertEqual(output['cleaned'], 'sesame seed')
        self.assertEqual(output['volume'], 0.0938)

    def test_spelled_fractions_1(self):
        test_string = 'One fourth cups milk'
        output = return_details(test_string)
        self.assertEqual(output['volume'], 0.25)

    def test_spelled_fractions_2(self):
        test_string = 'One and a fourth cups milk'
        output = return_details(test_string)
        self.assertEqual(output['volume'], 1.25)

    def test_fraction_characters(self):
        test_string = '⅕ cups milk'
        output = return_details(test_string)
        self.assertEqual(output['volume'], 0.2)


class TestNonStandardMeasures(unittest.TestCase):
    """Tests for vague measures like "a pinch" or "a few dabs"
    """
    def test_pinches_1(self):
        test_string = 'Pinch of salt'
        output = return_details(test_string)
        self.assertEqual(output['weight'], 3.0)

    def test_pinches_2(self):
        test_string = '2 pinches salt'
        output = return_details(test_string)
        self.assertEqual(output['weight'], 6.0)

    def test_pinches_3(self):
        test_string = 'A few pinches of salt'
        output = return_details(test_string)
        self.assertEqual(output['weight'], 9.0)

    def test_drizzle(self):
        test_string = 'A generous drizzle of balsamic vinegar'
        output = return_details(test_string)
        self.assertEqual(output['weight'], 3.0)
        self.assertEqual(output['cleaned'], 'balsamic vinegar')

    def test_sticks(self):
        test_string = '5 sticks of butter'
        output = return_details(test_string)
        self.assertEqual(output['weight'], 567)
        self.assertEqual(output['cleaned'], 'butter')

    def test_slices(self):
        test_string = '4 1/2in thick slices country white bread'
        output = return_details(test_string)
        self.assertEqual(output['weight'], 120)
        self.assertEqual(output['cleaned'], 'white bread')

    def test_cloves(self):
        test_string = '8 garlic cloves, peeled and sliced paper thin'
        output = return_details(test_string)
        self.assertEqual(output['weight'], 40)
        self.assertEqual(output['cleaned'], 'garlic')

        test_string = '8 large garlic cloves, peeled and sliced paper thin'
        output = return_details(test_string)
        self.assertEqual(output['weight'], 40)
        self.assertEqual(output['cleaned'], 'garlic')

        test_string = '8 cloves of garlic'
        output = return_details(test_string)
        self.assertEqual(output['weight'], 40)
        self.assertEqual(output['cleaned'], 'garlic')

        test_string = '1/2 garlic clove, smashed and very finely chopped'
        output = return_details(test_string)
        self.assertEqual(output['weight'], 2.5)
        self.assertEqual(output['cleaned'], 'garlic')

        test_string = '1/2 teaspoon ground cloves'
        output = return_details(test_string)
        self.assertEqual(output['cleaned'], 'clove')

        test_string = '2 whole cloves'
        output = return_details(test_string)
        self.assertEqual(output['weight'], 1)
        self.assertEqual(output['cleaned'], 'clove')


class TestNoMeasures(unittest.TestCase):
    """Tests for counts of items, having no weight or volume.
    Counts then converted to weight via the conversion table.
    """
    def test_counts(self):
        test_string = '3 onion'
        output = return_details(test_string)
        self.assertEqual(output['count'], 3.0)


class TestMultipleMeasures(unittest.TestCase):
    """Tests containing multiple measurements.
    Prefers those listed in cups or grams.
    """
    def test_volumes_and_weights_1(self):
        test_string = '4 to 5 cups/0.9 kilos to 1.1 kg all-purpose flour'
        output = return_details(test_string)
        self.assertEqual(output['volume'], 4.5)
        self.assertEqual(output['weight'], 1000)
        self.assertEqual(output['cleaned'], 'flour')

    def test_volumes_and_weights_2(self):
        test_string = '10 cups sugar (2.2 kilos)'
        output = return_details(test_string)
        self.assertEqual(output['volume'], 10)
        self.assertEqual(output['weight'], 2200)
        self.assertEqual(output['cleaned'], 'sugar')

    def test_multiple_volumes(self):
        test_string = '1 1/5 cup/11fl oz/300ml heavy cream'
        output = return_details(test_string)
        self.assertEqual(output['volume'], 1.2)
        self.assertEqual(output['cleaned'], 'heavy cream')

    def test_measures_commas(self):
        test_string = '2 cups, 10 ounces, shredded Monterey Jack'
        output = return_details(test_string)
        self.assertEqual(output['cleaned'], 'monterey jack')
        self.assertEqual(output['volume'], 2)
        self.assertEqual(output['weight'], 283.4)


class TestSequentialNumberPatterns(unittest.TestCase):
    """Tests where multiple numbers appear in a row,
    or numbers later in the string apply to an earlier number.
    """

    def test_two_numbers_1(self):
        test_string = '2 100 gram cans milk'
        output = return_details(test_string)
        self.assertEqual(output['weight'], 200.0)

    def test_two_numbers_2(self):
        test_string = '2 1/2 cups milk'
        output = return_details(test_string)
        self.assertEqual(output['volume'], 2.5)

    def test_three_numbers(self):
        test_string = '3 2 1/2 gram nuts'
        output = return_details(test_string)
        self.assertEqual(output['weight'], 7.5)

    def test_numbers_in_parens_1(self):
        test_string = '3 (100 gram) bags flour'
        output = return_details(test_string)
        self.assertEqual(output['weight'], 300.0)
        self.assertEqual(output['cleaned'], 'flour')

    def test_numbers_in_parens_2(self):
        test_string = '1/2 (200-gram) can black beans'
        output = return_details(test_string)
        self.assertEqual(output['weight'], 100)
        self.assertEqual(output['cleaned'], 'black bean')

        test_string = '1 1/2 (200g) cans black beans'
        output = return_details(test_string)
        self.assertEqual(output['weight'], 300)
        self.assertEqual(output['cleaned'], 'black bean')

    @unittest.skip('one-off parens pattern')
    def test_numbers_in_parens_3(self):
        test_string = '1 (19.5) oz. Pillsbury® Family Size Chocolate Fudge '\
            'Brownie Mix'
        output = return_details(test_string)
        self.assertEqual(output['cleaned'], 'chocolate fudge brownie mix')
        self.assertEqual(output['weight'], 500)

    def test_each_count(self):
        test_string = '3 bags flour, about 100 grams each'
        output = return_details(test_string)
        self.assertEqual(output['weight'], 300.0)

    def test_plus_pattern(self):
        test_string = '1/3 cup plus 1 tablespoon extra-virgin olive oil'
        output = return_details(test_string)
        self.assertEqual(output['volume'], 0.3958)
        self.assertEqual(output['cleaned'], 'olive oil')


class TestRemovingDescriptors(unittest.TestCase):
    """Tests for removing unnecessary description words.
    """
    def test_removes_container_words(self):
        test_string = '2 100 gram cans of milk'
        output = return_details(test_string)
        self.assertEqual(output['cleaned'], 'milk')

    def test_removes_descriptor_words(self):
        test_string = '2 sticks of melted softened butter'
        output = return_details(test_string)
        self.assertEqual(output['cleaned'], 'butter')

    def test_removes_adverb_words(self):
        test_string = '2 cups finely chopped shallots'
        output = return_details(test_string)
        self.assertEqual(output['cleaned'], 'shallot')

    def test_removes_compound_words(self):
        test_string = '1 large low -fat, high-fiber, burrito-size tortilla'
        cleaned = return_details(test_string)['cleaned']
        self.assertEqual(cleaned, 'tortilla')

        test_string = '2 cups ready-to-serve creamy tomato soup'
        cleaned = return_details(test_string)['cleaned']
        self.assertEqual(cleaned, 'tomato soup')

        test_string = '2 cups no-salt-added fat-added thick-cut potato chips'
        cleaned = return_details(test_string)['cleaned']
        self.assertEqual(cleaned, 'potato chip')

        test_string = '2 cups all-in-one oven-to-table potato chips'
        cleaned = return_details(test_string)['cleaned']
        self.assertEqual(cleaned, 'potato chip')

    def test_removes_for(self):
        test_string = '1 tbsp coconut oil for frying'
        cleaned = return_details(test_string)['cleaned']
        self.assertEqual(cleaned, 'coconut oil')

        test_string = '1/2 cup vegetable oil for frying, or as needed'
        cleaned = return_details(test_string)['cleaned']
        self.assertEqual(cleaned, 'vegetable oil')

    def test_removes_such_as(self):
        test_string = '1 cup high-quality mustard such as colemans'
        cleaned = return_details(test_string)['cleaned']
        self.assertEqual(cleaned, 'mustard')

    def test_removes_like(self):
        test_string = '1 cup high-quality mustard like colemans'
        cleaned = return_details(test_string)['cleaned']
        self.assertEqual(cleaned, 'mustard')

    def test_removes_brand(self):
        test_string = '1 cup Crisco® vegetable shortening'
        cleaned = return_details(test_string)['cleaned']
        self.assertEqual(cleaned, 'vegetable shortening')

        test_string = '1 cup Coleman\'s mustard'
        cleaned = return_details(test_string)['cleaned']
        self.assertEqual(cleaned, 'mustard')

    def test_removes_multiple_descriptors(self):
        test_string = '1/2 pound skinned and boned smoked trout'
        cleaned = return_details(test_string)['cleaned']
        self.assertEqual(cleaned, 'smoked trout')

    def test_removes_after_at(self):
        test_string = '1 cup european butter available at specialty stores'
        cleaned = return_details(test_string)['cleaned']
        self.assertEqual(cleaned, 'butter')

    def test_removes_with_commas(self):
        test_string = '3 cups peeled, cored, and thickly sliced apples'
        cleaned = return_details(test_string)['cleaned']
        self.assertEqual(cleaned, 'apple')

        test_string = '1 cup sliced and firmly packed, ripe banana'
        cleaned = return_details(test_string)['cleaned']
        self.assertEqual(cleaned, 'banana')


class QuickTest(unittest.TestCase):
    @unittest.skip('Difficult examples')
    def quick_test(self):
        """Just a place to hold some troublesome examples
        """
        test_string = '1 1/2 cups picked lump, backfin, or jumbo lump crab '\
            'meat'
        test_string = '2 1/2 cups all-purpose flour plus more for pan'
        test_string = '1 cup whole, peeled garlic cloves, roasted in 1/4 cup '\
            'olive oil and 1/4 cup white wine'
        test_string = '1 omega-3-enriched egg, scrambled in 1 tsp '\
            'trans-fat-free margarine'
        test_string = '1/2 pound sliced, thick-deli-cut or rotisserie turkey '\
            'breast, chopped'
        pass


class TestApplyingMultiplier(unittest.TestCase):
    """Tests where a multiplier is added based on descriptor words.
    """
    def test_volume_increases(self):
        test_string1 = '2 cups flour'
        baseline = return_details(test_string1)['volume']

        test_string2 = '2 firmly packed cups flour'
        test_volume = return_details(test_string2)['volume']
        self.assertEqual(test_volume, 2.4)
        self.assertTrue(test_volume > baseline)

    def test_volume_decreases(self):
        test_string1 = '2 cups flour'
        baseline = return_details(test_string1)['volume']

        test_string2 = '2 scant cups flour'
        test_volume = return_details(test_string2)['volume']
        self.assertEqual(test_volume, 1.8)
        self.assertTrue(test_volume < baseline)

    def test_count_increases(self):
        test_string1 = '2 onions'
        baseline = return_details(test_string1)['count']

        test_string2 = '2 large onions'
        test_count = return_details(test_string2)['count']
        self.assertEqual(test_count, 2.4)
        self.assertTrue(test_count > baseline)

    def test_count_decreases(self):
        test_string1 = '2 onions'
        baseline = return_details(test_string1)['count']

        test_string2 = '2 very small onions'
        test_count = return_details(test_string2)['count']
        self.assertEqual(test_count, 1.6)
        self.assertTrue(test_count < baseline)


class TestAvoidingOverlappingRules(unittest.TestCase):
    """Tests where multiple parsing rules apply.
    """
    def test_sticks_and_each(self):
        test_string = '2 sticks butter, each 5000 grams'
        weight = return_details(test_string)['weight']
        self.assertEqual(weight, 226.8)

    def test_each_and_removal(self):
        test_string = '6 skinless, boneless chicken breasts (10 ounces each)'
        details = return_details(test_string)
        self.assertEqual(details['weight'], 1700.4)
        self.assertEqual(details['cleaned'], 'chicken')

    def test_weight_and_count(self):
        test_string = '2 lbs kohlrabies (about 5 medium)'
        details = return_details(test_string)
        self.assertEqual(in_grams['lb'] * 2, 907.18)
        self.assertEqual(details['weight'], 907.18)
        self.assertEqual(details['cleaned'], 'kohlraby')

    def test_weight_span_three_num(self):
        test_string = '1 3-1/2 to 4 pound pork shoulder'
        details = return_details(test_string)
        self.assertEqual(round(in_grams['lb'] * 3.75, 2), 1700.96)
        self.assertEqual(details['weight'], 1700.9625)
        self.assertEqual(details['cleaned'], 'pork')

    def test_multiple_volumes_and_weights(self):
        test_string = '1 cup plus 2 tablespoons (9 oz / 255 g) lukewarm water'
        details = return_details(test_string)
        self.assertEqual(details['weight'], 255)
        self.assertEqual(details['volume'], 1.125)
        self.assertEqual(details['cleaned'], 'water')

        test_string = '1/3 cup plus 1 1/2 cups grated Parmesan'
        details = return_details(test_string)
        self.assertEqual(details['volume'], 1.8333)
        self.assertEqual(details['cleaned'], 'parmesan')

        test_string = '2 pounds plus 1/2 cup grated Parmesan'
        details = return_details(test_string)
        self.assertEqual(details['volume'], 0.5)
        self.assertEqual(details['weight'], 907.18)

    def test_span_and_combining_numbers(self):
        # First 4 1/2 -> 4.5
        # 4.5 -to 5 -> 4.75
        self.assertEqual(round(in_grams['lb'] * 4.75, 4), 2154.5525)
        test_string = '1 4 1/2-to 5-pound whole turkey breast'
        details = return_details(test_string)
        self.assertEqual(details['weight'], 2154.5525)
        self.assertEqual(details['cleaned'], 'turkey')

    def test_long_descriptors_or(self):
        test_string = '1/2 pound sliced, thick-deli-cut or rotisserie turkey '\
            'breast, chopped'
        cleaned = return_details(test_string)['cleaned']
        self.assertEqual(cleaned, 'turkey')


class TestMultipleIngredients(unittest.TestCase):
    """Tests where multiple ingredients are present
    """
    def test_or_pattern_1(self):
        test_string = '3 (15.1/2-ounce) cans kidney or pinto beans'
        details = return_details(test_string)
        self.assertEqual(details['cleaned'], 'pinto bean')

    def test_or_pattern_2(self):
        test_string = '1 cup red, orange/yellow, or green bell peppers'
        details = return_details(test_string)
        self.assertEqual(details['cleaned'], 'green bell pepper')

        test_string = '8 ounces fresh morel mushrooms, halved if large, or 1 '\
            'ounce dried morels'
        details = return_details(test_string)
        self.assertEqual(details['cleaned'], 'morel mushroom')

    def test_or_pattern_3(self):
        test_string = '1 whole side of salmon, or 4 (6-ounce) salmon fillets'
        details = return_details(test_string)
        self.assertEqual(details['cleaned'], 'salmon')
        self.assertEqual(details['weight'], 680.16)

        test_string = '10 fresh sage leaves, or 1/2 teaspoon dried sage'
        details = return_details(test_string)
        self.assertEqual(details['cleaned'], 'sage')
        self.assertEqual(round(details['weight'], 4), 30)

    def test_or_pattern_4(self):
        test_string = '2 or 3 sprigs mint, regular or spicy'
        details = return_details(test_string)
        self.assertEqual(details['cleaned'], 'mint')

    def test_or_pattern_5(self):
        test_string = '1 pint grape tomatoes, or sweet 100 tomatoes or pear '\
            'tomatoes'
        details = return_details(test_string)
        self.assertEqual(details['cleaned'], 'grape tomato')
        self.assertEqual(details['volume'], 2)

    def test_or_pattern_6(self):
        test_string = '1 jalapeno pepper, seeded and diced, or to taste'
        details = return_details(test_string)
        self.assertEqual(details['cleaned'], 'jalapeno pepper')

    def test_or_pattern_7(self):
        test_string = '1/4 cup natural cane sugar or packed organic light '\
            'brown sugar'
        details = return_details(test_string)
        self.assertEqual(details['cleaned'], 'light brown sugar')

        test_string = '1 cup heavy or whipping cream'
        details = return_details(test_string)
        self.assertEqual(details['cleaned'], 'whipping cream')

    def test_eggs(self):
        test_string = '5 egg whites plus 2 egg yolks'
        details = return_details(test_string)
        self.assertEqual(details['cleaned'], 'egg')
        self.assertEqual(details['weight'], 190)


class TestConversionTableLookup(unittest.TestCase):
    """Test converting volumes and counts to grams
    the conversion table.
    NOTE: currently stubbing in a rough average conversion.
    """
    # Mocked table return results
    expected_rows = [('1 cup', 160), ('1 medium', 110)]

    # Until conversion table is healthier, return an average ish
    # volume/count to grams
    #   Volume - 180 grams/cup
    #   Count  - 120 grams/count
    def test_stub_lookup(self):
        test_volume = '2 cups onions'
        output = return_details(test_volume)
        self.assertEqual(output['weight'], 360)

        test_count = '2 onions'
        output = return_details(test_count)
        self.assertEqual(output['weight'], 240)

    def test_no_lookup_when_weight_provided(self):
        test_string = '200 grams onion'
        output = return_details(test_string, self.expected_rows)
        self.assertEqual(output['weight'], 200)

    @unittest.skip('table currently stubbed')
    def test_cup_conversion(self):
        test_string = '2 cup onions'
        output = return_details(test_string, self.expected_rows)
        self.assertEqual(output['weight'], 320)

    @unittest.skip('table currently stubbed')
    def test_count_conversion(self):
        test_string = '2 onion'
        output = return_details(test_string, self.expected_rows)
        self.assertEqual(output['weight'], 220)


if __name__ == '__main__':
    unittest.main()
