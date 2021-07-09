from abc import ABCMeta, abstractmethod
from bs4 import BeautifulSoup
from psycopg2 import pool
import json
import os
import re


class BaseScraper(metaclass=ABCMeta):
    def __init__(self, soup, domain, path, read_path, pool_conn):
        """Initialize the scraper class
        An inheriting class must include these methods:
        - gather_title
        - gather_ingredients
        - gather_instructions
        - gather_misc

        Parameters
        ----------
        soup [bs4.BeautifulSoup]: soup object of the given recipe page
        domain [str]: domain sourcing the page
        path [str]: url path specific to the recipe
        read_path [str]: where to find downloaded files
        pool_conn [psycopg2.pool.SimpleConnectionPool]: connection to the
            database
        """
        self.soup = soup
        self.domain = domain
        self.path = path
        self.read_path = read_path
        self.pool_conn = pool_conn

    def stripped_text(self, element):
        """Gather text and clean its whitespaces from a bs4 element

        Parameters
        ----------
        element [bs4.element.Tag]: element containing text

        Returns
        -------
        [str or None]: any text found within the element with whitespace
            compressed/replaced with a single whitespace and stripped from
            the left and right
        """
        if not element:
            return None
        # Replace/compress whitespace with/into a single space
        return re.sub(r"\s+", ' ', element.get_text()).strip()

    def assemble_primary(self):
        """Assembles all of the components a recipe must include:
        - title
        - ingredients
        - instructions
        - misc (potentially not needed)
        """
        self.title = self.gather_title()
        self.ingredients = self.gather_ingredients()
        self.instructions = self.gather_instructions()
        self.misc = self.gather_misc()

    @abstractmethod
    def gather_title(self):
        pass

    @abstractmethod
    def gather_ingredients(self):
        """Dict following the layout
        {'part_1': ['ingredient line 1', 'ingredient line 2', '...'],
         '...' : [...]}
        """
        pass

    @abstractmethod
    def gather_instructions(self):
        """Dict following the layout
        {'part_1': ['instruction line 1', 'instruction line 2', '...'],
         '...' : [...]}
        """
        pass

    @abstractmethod
    def gather_misc(self):
        """Potential keys:
        - image [str; path to image]
        - prep_time [int; minutes after cleaning]
        - cook_time [int; minutes after cleaning]
        - author [str]
        - course [str]
        - cuisine [str]
        - description [str]
        - servings [int; after cleaning]
        - rating [float; relative to 100%]
        - ratings [integer; count]
        - make_again [float; percentage]
        """
        pass

    def insert_recipe(self):
        """Insert a parsed recipe into the "recipes" table
        """
        try:
            conn = self.pool_conn.getconn()
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO recipes (
                        domain,
                        path,
                        title,
                        ingredients,
                        instructions,
                        misc
                    ) VALUES (
                        %(domain)s,
                        %(path)s,
                        %(title)s,
                        %(ingredients)s,
                        %(instructions)s,
                        %(misc)s
                    )""", {
                        'domain': self.domain,
                        'path': self.path,
                        'title': self.title,
                        'ingredients': json.dumps(self.ingredients),
                        'instructions': json.dumps(self.instructions),
                        'misc': json.dumps(self.misc)
                })
                conn.commit()
            self.pool_conn.putconn(conn)
        except Exception as error:
            self.log_scraper_error(self.path, error)

    def log_scraper_error(self, path, error):
        """Write errors to a file for later viewing
        Json lines format for easy reading into Pandas later on
        """
        error_dict = {
            'path': path,
            'error_type': error.__class__.__name__,
            'error_message': error.args
        }
        with open(f"{self.read_path}/scraper_errors.jsonl", 'a') as f:
            f.write(json.dumps(error_dict) + "\n")

    def close_connection_pool(self):
        """Closes the  Sql Pool Manager
        """
        self.pool_conn.closeall()
