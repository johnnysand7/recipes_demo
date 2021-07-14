# Recipes
---
The overall goals of the project are:
- parse recipe ingredient lines into `amount`s and clean `ingredient` names
- convert any volume amounts to grams via a conversion table
- crawl recipe sites and scrape recipes into a clean standardized schema
- convert recipes into ingredients by their percent total weight (or just as grams)
- implement an accurate search by individual ingredients
- create "averaged" recipes with similar titles for fun experiments (or a complete mess)

---

### Parsing
Parsing is done entirely through regular expressions as the vast majority
of ingredient lines follow fairly specific patterns:
```
{amount} {ingredient name}, {unneeded modifiers}
```

The main challenge is accounting for variations like
```
# All meaning "1.5 cups flour":
1 1/2 cups flour
One and a half c flour
1 ½c. flour

# All meaning "One 0.5 pound chicken breast":
1 1/2 pound chicken breast
One half-lb chicken breast
8oz chicken breast
```
so the context of weight versus volume and ingredient type matters.

The next challenge is accurately converting volumes to weights:
```
1 cup water == 237 grams
1 cup flour == 120 grams
1 cup sugar == 201 grams
```
These kinds of conversions are stored in a lookup table. Data is sourced from  places like:
- [AllRecipe's conversion tables](https://www.allrecipes.com/article/ounces-to-cups-and-other-cooking-conversions/)
- [USDA portions and weights](https://www.ars.usda.gov/northeast-area/beltsville-md-bhnrc/beltsville-human-nutrition-research-center/food-surveys-research-group/docs/fndds-download-databases/)
  - lots of cleaning needed but useful

`ingredient_parser_test.py` includes a lot of these variations. Essentially all tests currently pass
aside from those marked to skip.

Ultimately an ingredient and volume-weight conversion table will be stored
in PostgreSql or maybe Redis; something like 1,000 unique ingredients
account for ~90% or more of all ingredients in a set of 100k recipes I've
looked at, so the table will not need to be large to be effective.

---

### Crawling and Scraping
Crawling and scraping are both performed with Python, with the final scraped
data stored in a table in PostgreSql.

Most recipe sites have indexes or nice search pages, so crawling is often
more like iterating through directed pages. A `sleep` time of 1 second is added between
pages as some of the sites I'm looking are some of my favorite smaller blog-like sites,
so I don't want to hammer them with requests too quickly.

Occasionally Selenium is needed to interact with dynamic pages to click
buttons and scroll to ensure a page loads entirely.

The `base_crawler.py` / `base_crawler_test.py` files show examples of general crawling,
while `epicurious.py` / `epicurious_test.py` is a more directed crawl.

---

### Example Schema

For the `recipes` table, the main components to collect are:
- `domain`: domain of the crawled site
- `path`: specific url path on a domain, together creating a primary key
- `title`: title text of the recipe
- `ingredients`: json of ingredients grouped under specific recipe parts
- `instructions`: json of instructions grouped under specific recipe parts
- `misc`: json of other items to explore later:
  - `image`
  - `description`
  - `cuisine`
  - `cook_time` and `prep_time`
  - `author`
  - `rating`
  - `rating_count`
  - `make_again_percent`


Eventually I'd like to parse ratings and add fields like ingredient counts
to aid in searches; perhaps filtering by rating as well as recipe complexity.

---
