# Recipes
---
The overall goals of the project are:
- parse recipe ingredient lines into `amount`s and clean `ingredient` names
- convert any volume amounts to grams via a conversion table
- crawl recipe sites and scrape recipes into a clean schema
- convert recipes into ingredients by percent total weight
- implement an accurate search by individual ingredients
- create "averaged" recipes with similar titles

---

### Parsing
Parsing is done entirely through regular expressions as the vast majority
of ingredient lines follow specific patterns:
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

`ingredient_parser_test.py` includes a lot of these variations.

Ultimately an ingredient and volume-weight conversion table will be stored
in PostgreSql or maybe Redis; something like 1,000 unique ingredients
account for ~80% or more of all ingredients in a set of 100k recipes I've
looked at, so the table will not need to be large.

---

### Crawling and Scraping
Crawling and scraping are both performed with Python, with the final parsed
data stored in PostgreSql.

Most recipe sites have indexes or nice search pages, so crawling is often
more like iterating through pages.

Occasionally Selenium is needed to interact with dynamic pages to click
buttons and scroll to ensure a page loads entirely.

See `epicurious.py` for an example.

---

### Example Schema

The main components to collect are:
- `title`
- `ingredients`
- `instructions`

Other fields that are gathered when available are:
- `image`
- `description`
- `cook_time` and `prep_time`
- `author`
- `rating`, `rating_count`, and `make_again_percent`


Eventually I'd like to parse ratings and add fields like ingredient counts
to aid in searches; perhaps filtering by rating as well as recipe complexity.

---
