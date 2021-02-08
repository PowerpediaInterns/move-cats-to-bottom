# imports
import pywikibot
import requests
import re
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# the number of pages this bot will go through before stopping
PAGES_TO_GO_THROUGH = 25
# the title of the page that stores the last page this bot has seen 
# and where to pick up on a later execution
STORAGE_PAGE = "CatMoverBotInfo"


class MoveCatsBot:
    '''
    Moves all categories on any page to the bottom of that page.
    Useful to maintain formatting for many pages that 
    list links to all categories at the bottom. 
    '''

    def __init__(self, site: pywikibot.site.APISite, reference_page_title: str):
        self.site = site
        self.api_url = site.protocol() + "://" + site.hostname() + site.apipath()
        self.reference_page_title = reference_page_title
    
    def pages_from(self, start_point: str) -> "page generator":
        '''
        Returns a generator with 25 pages starting from
        the given page.
        '''
        my_session = requests.Session()

        api_arguments= {
            "action": "query",
            "format": "json",
            "list": "allpages",
            "apfrom": start_point,
            "aplimit": PAGES_TO_GO_THROUGH
        } 

        request = my_session.get(url=self.api_url, params=api_arguments, verify=False)
        data = request.json()

        pages = data["query"]["allpages"]
        return pages

    def get_page_start(self) -> str:
        '''
        Returns the page that this bot is supposed to start editing from,
        according to this bot's reference page. 
        '''
        page = pywikibot.Page(self.site, self.reference_page_title)
        return page.text.split('\n')[0]
    
    def set_page_start(self, new_start: str) -> None:
        '''
        Sets the page that this bot will start from next to the string given.
        '''
        page = pywikibot.Page(self.site, self.reference_page_title)
        page.text = new_start
        page.save("Store new page from last execution.")

    def run(self) -> None:
        '''
        Runs the bot on a certain number of pages.
        Records the last page the bot saw on a certain Mediawiki page.
        '''
        start_page_title = self.get_page_start()
        last_page_seen = ""

        pages_to_run = self.pages_from(start_page_title)

        for page in pages_to_run:
            last_page_seen = page['title']
            self.move_cats(last_page_seen)
        
        if len(list(pages_to_run)) < PAGES_TO_GO_THROUGH:
            # if we hit the end, then loop back to beginning
            self.set_page_start("")
        else:
            # otherewise, just record the last page seen
            self.set_page_start(last_page_seen)












    
    def split_into_cats(self, line: str) -> [str]:
        """
        Splits a line into its potential categories. 
        Example:
        [[Category:X]] [[Category:Y]]
            -> ["[[Category:X]]", "[[Category:Y]]"]
        """

        proto_cats = line.split("]]")
        potential_cats = []

        for proto_cat in proto_cats:
            potential_cats.append(proto_cat + "]]")
        
        return potential_cats
    
    def find_cat(self, line: str) -> str:
        '''
        Given a line in a wiki page,
        uses regex to get any categories in the line. 
        '''
        regex_string = r"(.*)(\[\[Category\:([^\[\]]*)\]\])(.*)"
        line_matches = re.match(regex_string, line)

        category = None

        if line_matches is not None:
            category = line_matches.group(2)

        return category

    def is_reference_line(self, line: str) -> bool:
        '''
        Returns true if the line in question represents the
        beginning of a "references" section.
        Returns false otherwise.
        '''
        line = line.lower()

        # check 1: ==References== pages
        valid_reference_titles = set([
            "==references==",
            "== references==",
            "==references ==",
            "== references =="
        ])
        if line in valid_reference_titles:
            return True

        # check 2: {{reflist}} templates
        regex_string = r"(.*)(\{\{reflist)(.*)"
        x = re.match(regex_string, line)

        if x is not None:
            return True
        
        return False

    def move_cats(self, page_name: str) -> None:
        '''
        Moves all categories on the given page to the bottom.
        '''
        # get page text
        page = pywikibot.Page(self.site, page_name)
        page_lines = page.text.split('\n')

        # get categories in page text
        detected_categories = []

        should_be_moving = False

        # loop through all lines
        for line in reversed(page_lines):
            # find categories to move
            potential_cats = self.split_into_cats(line)

            # check everything except the last part
            for potential_cat in potential_cats[:-1]:
                # find the category name
                detected_category = self.find_cat(potential_cat)

                # if we reach an area without categories,
                # start moving 
                if line.strip() != detected_category and not should_be_moving:
                    should_be_moving = True

                # remove the category from where it is
                if detected_category is not None:
                    if should_be_moving:
                        detected_categories.append(detected_category)
                        page.text = page.text.replace(detected_category, "")
            
            if potential_cats[-1].strip() != "]]" and not should_be_moving:
                # if there is still something leftover at the end
                should_be_moving = True
        
        # remove any blank space at the end of the page before we 
        # add anything new
        page.text = page.text.rstrip('\n')
        
        # if we found any categories, make edits
        if len(detected_categories) > 0:
            # re-attach all categories to the bottom of the page
            for cat in detected_categories:
                page.text += ('\n' + cat)
            
            # save edits
            page.save("Add all categories to the bottom of the page. ")


if __name__ == "__main__":
    MoveCatsBot(
        pywikibot.Site(),
        STORAGE_PAGE
    ).run()

