from base_crawler import *
from base_scraper import *


class EpicuriousCrawler(BaseCrawler):
    def crawl_domain(self, page_number=1):
        """Iterate through search pages; end when no more pages are found
        Only download "/recipes/" links

        Parameters
        ----------
        page_number [int; default 1]: the search page number to start on
        """
        # Iterate though pages; if already completed, skip
        while True:
            # Set a hard limit incase the 404 landing page changes
            # ~10 pages more than the last check of the site
            if page_number > 2500:
                print('Page limit reached before finding the "Dont Cry" page')
                break

            # TODO: implement a check for recrawling to stop once many
            # previously downloaded pages have been found

            next_path = f'/search?page={page_number}'
            if r.sismember(self.rkey(1), next_path):
                # already checked; continue to the next page
                page_number += 1
                continue
            current_url = f"{self.base_url}{next_path}"

            try:
                response = self.get_response(current_url)

                # Check if a single redirection occurred
                if response.retries.redirect == 0:
                    next_path = self.handle_redirection(next_path, response)
                print(response.status)
                html = response.data
            except Exception as e:
                self.log_crawler_error(next_path, e)
                print(f"\n{e.__class__.__name__}: {e.args}: {current_url}\n")
                r.sadd(self.rkey(2), next_path)
                r.srem(self.rkey(0), next_path)
                # Move on to the next search page
                page_number += 1
                continue

            soup = BeautifulSoup(html, features='lxml')
            if self.end_search_crawl(soup):
                print('Reached the final search page')
                break

            if self.find_more_links:
                self.add_links(soup)

            self.download_page(html, next_path)
            self.complete_page(next_path)
            print(f"Completed download of {next_path}")

            # # Move on to the next search page and slow things down
            page_number += 1
            sleep(1)

        return None

    def end_search_crawl(self, soup):
        """Check for the "Don't Cry" header
        Use regex for slight variations just in case
        """
        return soup.find('h1', text=re.compile(r"Don't\s+Cry", flags=re.I))

    def download_recipes(self):
        """For this crawler, pages here are the final recipe pages;
        no need to collect additional links
        """
        while r.scard(self.rkey(0)) > 0:
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
                self.log_crawler_error(next_path, e)
                print(f"\n{e.__class__.__name__}: {e.args}: {current_url}\n")
                r.sadd(self.rkey(2), next_path)
                r.srem(self.rkey(0), next_path)
                continue

            soup = BeautifulSoup(html, features='lxml')
            self.download_page(soup, next_path)
            self.complete_page(next_path)
            print(f"Completed download of {next_path}")

            sleep(1)

    def download_page(self, soup, path):
        """Download a trimmed version of the html, starting
        at 'div.main-content'

        Downloads the page's image when present

        Parameters
        ----------
        soup [bs4.BeautifulSoup]: soup object for the current page
        path [str]: url path for the current page
        """
        file_name = path.lstrip('/').replace('/', '_-_')
        main_content = soup.select_one('div.main-content')
        if not main_content:
            print(f"Missing  'div.main-content' for {path}")
            main_content = soup

        self.download_image(main_content, path, file_name)

        with open(f"{self.download_path}/{file_name}.html", 'w') as f:
            f.write(str(main_content))

    def download_image(self, soup, path, file_name):
        """When present, download the image for a given recipe

        Parameters
        ----------
        see `download_page` above
        file_name [str]: file name based on the page's url path
        """
        img = soup.select_one('div.recipe-image img')
        if not img or not img.get('srcset', None):
            return None
        img_url = img.get('srcset', None)
        _, img_dom, img_path = self.url_parts(img_url)
        if not img_dom:
            img_url = f"{self.base_url}{img_path}"

        img_file_name = "{}/{}.{}".format(self.download_path,
                                          file_name,
                                          img_path.split('.')[-1])

        if os.path.exists(img_file_name):
            # Already downloaded
            return None
        try:
            response = self.get_response(img_url)
        except Exception as e:
            self.log_crawler_error(next_path, e, note='image')
            return None

        # Write the image if no errors have occured
        with open(img_file_name, 'wb') as f:
            f.write(response.data)


class EpicuriousScraper(BaseScraper):
    def gather_title(self):
        """The cleaned version of the page's h1 tag
        """
        return self.stripped_text(self.soup.h1)

    def gather_ingredients(self):
        """Ingredients come in groups, some with names and some without

        Returns
        -------
        ingredients [dict]: keys are ingredient group names
            (or a generic name) and values are lists of strings for that group
        """
        groups = self.soup.select(
            'div.ingredients-info ol.ingredient-groups li.ingredient-group'
        )
        if not groups:
            return None
        ingredients = {}
        for i, group in enumerate(groups):
            group_name = self.stripped_text(group.select_one('strong'))
            if not group_name:
                group_name = f"part_{i + 1}"
            group_ingredients = []
            for li in group.select('li'):
                ingredient_text = self.stripped_text(li)
                if not ingredient_text or\
                   ingredient_text.startswith('Equipment'):
                    continue
                group_ingredients.append(ingredient_text)
            if not group_ingredients:
                continue
            ingredients[group_name] = group_ingredients

        return ingredients

    def gather_instructions(self):
        """Instructions come in groups, some with names and some without

        Returns
        -------
        instructions [dict]: keys are instruction group names
            (or a generic name) and values are lists of strings for that group
        """
        groups = self.soup.select(
            'div.instructions ol.preparation-groups li.preparation-group'
        )
        if not groups:
            return None
        instructions = {}
        for i, group in enumerate(groups):
            group_name = self.stripped_text(group.select_one('strong'))
            if not group_name:
                group_name = f"part_{i + 1}"

            group_instructions = []
            for li in group.select('li'):
                instruction_text = self.stripped_text(li)
                if not instruction_text:
                    continue
                group_instructions.append(instruction_text)
            if not group_instructions:
                continue
            instructions[group_name] = group_instructions

        return instructions

    def gather_misc(self):
        """At most will include
        - image
        - author names (separated by newlines)
        - description (multiple parts separated by newlines)
        - cook/prep time
        - rating/ratings count/make again percent
        - serving count

        Calls the various methods to complete the misc dict

        Returns
        -------
        misc [dict]: a fully filled misc dict
        """
        misc = {}
        summary_keys = [
            ('yield', 'servings'),
            ('active-time', 'prep_time'),
            ('total-time', 'cook_time')
        ]
        for page_key, misc_key in summary_keys:
            block = self.soup.select_one(
                f"dl.summary-data dd[class='{page_key}']"
            )
            if not block:
                continue
            misc[misc_key] = self.stripped_text(block)

        self.gather_author(misc)
        self.gather_description(misc)
        self.gather_ratings(misc)
        self.gather_image(misc)

        return misc

    def gather_author(self, misc={}):
        """There will occassionally be multiple authors;
        separate with newlines

        Parameters
        ----------
        misc [dict; default empty dict]: misc dict to add to; default as empty
            for individual method testing

        Returns
        -------
        misc [dict]: filled misc hash after updating in-place
        """
        authors = self.soup.select('cite.contributors a.contributor')
        if not authors:
            return None
        misc['author'] = "\n".join(
            [self.stripped_text(author) for author in authors]
        )
        return misc

    def gather_description(self, misc={}):
        """Gather descriptions as paragraphs separated by newlines

        Parameters
        ----------
        see `gather_author` above

        Returns
        -------
        see `gather_author` above
        """
        description_blocks = self.soup.select_one(
            'div[itemprop="description"]'
        )
        if not description_blocks:
            return None
        description_text = ''
        for block in description_blocks.children:
            # Skip non-text blocks
            if not block.name:
                continue
            # Separate paragraphs with a single newline
            block_text = self.stripped_text(block)
            if not block_text:
                continue
            description_text += block_text + "\n"

        # Just an empty string
        if not description_text or description_text.isspace():
            return None

        misc['description'] = description_text.strip()
        return misc

    def gather_ratings(self, misc={}):
        """Gather a rating (out of 4) and the number of ratings

        Parameters
        ----------
        see `gather_author` above

        Returns
        -------
        see `gather_author` above
        """
        count_block = self.soup.select_one(
            'div.review-rating span[itemprop="reviewCount"]'
        )
        if not count_block:
            return None
        rating_count = int(self.stripped_text(count_block))
        if rating_count > 0:
            rating = self.stripped_text(
                self.soup.select_one('div.review-rating span.rating')
            )
            rating = self.convert_rating(rating)
            if rating:
                misc['rating'] = rating

            make_again = self.stripped_text(
                self.soup.select_one('div.prepare-again-rating span')
            )
            make_again = self.convert_make_again(make_again)
            if make_again:
                misc['make_again'] = make_again

            misc['ratings'] = rating_count
        return misc

    def convert_rating(self, rating):
        """Convert a 'decimal/integer' string into a ratio

        Parameters
        ----------
        rating [str]: a rating string, e.g. '3/4'

        Returns
        -------
        [float between 0.0 and 1.0]: e.g. 0.75
        """
        if not rating:
            return None
        match = re.search(r"(?P<num>[\d.]+)\s*/\s*(?P<den>\d+)", rating)
        if not match:
            return None
        return float(match['num']) / int(match['den'])

    def convert_make_again(self, make_again):
        """Convert the percentage into a ratio

        Parameters
        ----------
        make_again [str]: percentage string, e.g. '93%'

        Returns
        -------
        [float between 0.0 and 1.0]: e.g. 0.93
        """
        if not make_again:
            return None
        match = re.search(r"(?P<per>[\d.]+)\s*%", make_again)
        if not match:
            return None
        return round(float(match['per']) * 0.01, 2)

    def gather_image(self, misc={}):
        """Store the image filename/location to be read later
        Images have already been downloaded

        Parameters
        ----------
        see `gather_author` above

        Returns
        -------
        see `gather_author` above
        """
        image_block = self.soup.select_one('div.recipe-image img')
        if not image_block:
            return None
        image_url = image_block.get('srcset')
        file_path = '/Users/johnny/Projects/reciplease/data/epicurious'
        file_name = self.data['path'].lstrip('/').replace('/', '_-_')
        file_type = image_url.split('.')[-1]
        image_location = f"{file_path}/{file_name}.{file_type}"
        if os.path.exists(image_location):
            misc['image_location'] = image_location
        misc['image_url'] = image_url
        return misc


if __name__ == "__main__":
    start_url = 'https://www.epicurious.com/search/?page=1'
    download_path = '/Users/johnny/Projects/reciplease/data/epicurious'
    # Only links containing one of these substrings are allowed to be followed
    allow_these = ['recipes/']
    # Block any of these (overruling above allowed substrings)
    crawler = EpicuriousCrawler(start_url,
                                download_path,
                                allow=allow_these,
                                limit=1000)
    crawler.crawl_domain()
    crawler.download_recipes()

    pool_conn = pool.SimpleConnectionPool(1,
                                          20,
                                          user='johnny',
                                          database='reciplease')
    # TODO: update this to use a separate thread to process recipes
    # as the crawler is running too
    for fn in os.listdir(download_path):
        if not fn.endswith('.html'):
            continue
        url_path = fn.replace('_-_', '/').rstrip('.html')
        with open(f"{download_path}/{fn}", 'r') as f:
            soup = BeautifulSoup(f.read(), features='lxml')
        scraper = EpicuriousScraper(soup,
                                    'www.epicurious.com',
                                    url_path,
                                    download_path,
                                    pool_conn)
        scraper.assemble_primary()
        scraper.insert_recipe()
