import sys
import os

from datetime import date, datetime
from flask import Flask, render_template, redirect, abort
from flask_flatpages import FlatPages
from flaskext.markdown import Markdown
from flask.ext.assets import Environment as AssetManager
from flask_frozen import Freezer


# configuration
REPO_NAME = "flask_blog_tester"
REPO = ""    # default REPO is '', while serving or building the '/' + REPO_NAME is assigned to it
APP_DIR = os.path.dirname(os.path.abspath(__file__))

#def parent_dir(path):
#    '''Return the parent of a directory.'''
#    return os.path.abspath(os.path.join(path, os.pardir))

PROJECT_ROOT = APP_DIR

# In order to deploy to Github pages, you must build the static files to
# the project root
FREEZER_DESTINATION = PROJECT_ROOT

# Since this is a repo page (not a Github user page),
# we need to set the BASE_URL to the correct url as per GH Pages' standards
FREEZER_BASE_URL = "http://localhost/{0}".format(REPO_NAME)
#FREEZER_BASE_URL = "http://localhost/"
FREEZER_REMOVE_EXTRA_FILES = False  # IMPORTANT: If this is True, all app files
                                    # will be deleted when you run the freezer

DEBUG = True
TESTING = True
ASSETS_DEBUG = DEBUG
FLATPAGES_AUTO_RELOAD = True
FLATPAGES_EXTENSION = '.md'
#FLATPAGES_ROOT = 'pages'
FLATPAGES_ROOT = os.path.join(APP_DIR, 'pages')
#FREEZER_RELATIVE_URLS = True
# App configuration
SECTION_MAX_LINKS = 12

app = Flask(__name__)
app.config.from_object(__name__)
pages = FlatPages(app)
freezer = Freezer(app)
markdown_manager = Markdown(app, extensions=['fenced_code'], output_format='html5',)
asset_manager = AssetManager(app)

###############################################################################
# Model helpers

def get_pages(pages, offset=None, limit=None, section=None, year=None):
    """ Retrieves pages matching passec criterias.
    """
    articles = list(pages)
    # assign section value if none was provided in the metas
    for article in articles:
        if not article.meta.get('section'):
            article.meta['section'] = article.path.split('/')[0]
    # filter unpublished article
    if not app.debug:
        articles = [p for p in articles if p.meta.get('published') is True]
    # filter section
    if section:
        articles = [p for p in articles if p.meta.get('section') == section]
    # filter year
    if year:
        articles = [p for p in articles if p.meta.get('date').year == year]
    # sort by date
    articles = sorted(articles, reverse=True, key=lambda p: p.meta.get('date',
        date.today()))
    # assign prev/next page in serie
    for i, article in enumerate(articles):
        if i != 0:
            if section and articles[i - 1].meta.get('section') == section:
                article.prev = articles[i - 1]
        if i != len(articles) - 1:
            if section and articles[i + 1].meta.get('section') == section:
                article.next = articles[i + 1]
    # offset and limit
    if offset and limit:
        return articles[offset:limit]
    elif limit:
        return articles[:limit]
    elif offset:
        return articles[offset:]
    else:
        return articles

def get_years(pages):
    years = list(set([page.meta.get('date').year for page in pages]))
    years.reverse()
    return years

def section_exists(section):
    return not len(get_pages(pages, section=section)) == 0

###############################################################################
# Routes

@app.route('/')
def index():
    return render_template('index.html', pages=pages, repo=REPO)

@app.route('/<path:path>/')
def page(path):
    # compute current "section" from path
    section = path.split('/')[0]
    #print(section)
    #print(list(pages))
    #print(path)
    page = pages.get_or_404(path)
    #print(page)
    # ensure an accurate "section" meta is available
    page.meta['section'] = page.meta.get('section', section)
    # allow preview of unpublished stuff in DEBUG mode
    if not app.debug and not page.meta.get('published', False):
        abort(404)
    template = page.meta.get('template', '%s/page.html' % section)
    return render_template(template, page=page, section=section)

@app.route('/<string:section>/')
def section(section):
    if section == 'blog':   # the blog page is not simple, it has to list down entries, so this method
        template = '%s/index.html' % section
        #template = '%s/page.html' % section

        if not section_exists(section) and not os.path.exists(template):
                abort(404)

        articles = get_pages(pages, limit=SECTION_MAX_LINKS, section=section)

        years = get_years(get_pages(pages, section=section))
        print years
        return render_template(template, pages=articles, years=years, repo=REPO)
    else:   # These section pages are just rendered MarkDown
        page = pages.get_or_404(section)

        # ensure an accurate "section" meta is available
        page.meta['section'] = page.meta.get('section', section)
        # allow preview of unpublished stuff in DEBUG mode
        if not app.debug and not page.meta.get('published', False):
            abort(404)
        template = page.meta.get('template', '%s/page.html' % section)
        return render_template(template, page=page, section=section)

@app.route('/tag/<string:tag>/')
def tag(tag):
    #articles = get_pages(pages, limit=SECTION_MAX_LINKS, section="blog")
    tagged = [p for p in pages if tag in p.meta.get('tags', [])]
    return render_template('tag.html', pages=tagged, tag=tag, repo=REPO)


#URL GENERATORS

@freezer.register_generator
def section():
    #print(section)
    for page in pages:
        section = page.path.split('/')[0]
        # ensure an accurate "section" meta is available
        section = page.meta.get('section', section)
        print(">>> Freezing section homepage: " + section)
        yield {'section': section}

@freezer.register_generator
def page():
    pages_path = os.path.join(app.root_path, 'pages')
    for page in list(os.walk(pages_path)):
        if len(page) >= 3:
            dir = page[0].split("/pages")[1]
            #print dir
            for file in page[2]:
                path = dir + '/' + file.split(".md")[0]
                print(">>> Freezing file: " + path)
                yield {'path': path}


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == "build":
        app.debug = False
        #REPO = '/'+REPO_NAME     # works great for github pages, but not for gleegue.org
        asset_manager.config['ASSETS_DEBUG'] = False
        freezer.freeze()
        #local("cp ./static/*.ico ./build/")
        #local("cp ./static/*.txt ./build/")
        #local("cp ./static/*.xml ./build/")
        print("Done.")
    elif len(sys.argv) > 1 and sys.argv[1] == "serve":
        REPO = '/' + REPO_NAME
        freezer.serve(port=4000)
    else:
        app.run(port=8000)
