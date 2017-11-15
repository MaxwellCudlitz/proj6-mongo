"""
Flask web app connects to Mongo database.
Keep a simple list of dated memoranda.

Representation conventions for dates: 
   - We use Arrow objects when we want to manipulate dates, but for all
     storage in database, in session or g objects, or anything else that
     needs a text representation, we use ISO date strings.  These sort in the
     order as arrow date objects, and they are easy to convert to and from
     arrow date objects.  (For display on screen, we use the 'humanize' filter
     below.) A time zone offset will 
   - User input/output is in local (to the server) time.  
"""

import flask
from flask import g
from flask import render_template
from flask import request
from flask import url_for
from flask import redirect

import json
import logging

import sys

# Date handling 
import arrow   
from dateutil import tz  # For interpreting local times

# Mongo database
from pymongo import MongoClient

import config
CONFIG = config.configuration()


MONGO_CLIENT_URL = "mongodb://{}:{}@{}:{}/{}".format(
    CONFIG.DB_USER,
    CONFIG.DB_USER_PW,
    CONFIG.DB_HOST, 
    CONFIG.DB_PORT, 
    CONFIG.DB)


print("Using URL '{}'".format(MONGO_CLIENT_URL))


###
# Globals
###

app = flask.Flask(__name__)
app.secret_key = CONFIG.SECRET_KEY

####
# Database connection per server process
###

try: 
    dbclient = MongoClient(MONGO_CLIENT_URL)
    db = getattr(dbclient, CONFIG.DB)
    collection = db.dated

except:
    print("Failure opening database.  Is Mongo running? Correct password?")
    sys.exit(1)



###
# Pages
###

@app.route("/")
@app.route("/index")
def index():

  app.logger.debug("Main page entry")
#   g.memos = get_memos()
#   for memo in g.memos: 
#       app.logger.debug("Memo: " + str(memo))
  return flask.render_template('index.html')


@app.route("/_create_memo", methods=['POST'])
def create_memo():
    """
    creates a new memo, inserts it into mongo, 
    and returns the current memo list as 
    formatted JSON
    """
    form = request.form
    date = form['date']
    memo = form['memo']
    record = {
        "type": "dated_memo",
        "date": arrow.get(date).naive,
        "text": memo
    }
    collection.insert(record)
    return retrieve_formatted_json_memos()

@app.route("/_retrieve_memos", methods=['GET'])
def retrieve_memos():
    """
    Returns formatted and humanized memos
    for the client. Only called when the
    page first loads.
    """
    return retrieve_formatted_json_memos()

def retrieve_formatted_json_memos():
    """
    returns a JSOn object that contains memos that have 
    been localized and humanized for the client
    """
    memos = get_memos()
    for memo in memos:
        memo['date'] = humanize_arrow_date(arrow.get(memo['date']))
    return flask.jsonify(memos)



@app.errorhandler(404)
def page_not_found(error):
    app.logger.debug("Page not found")
    return flask.render_template('page_not_found.html',
                                 badurl=request.base_url,
                                 linkback=url_for("index")), 404

#################
#
# Functions used within the templates
#
#################

@app.template_filter( 'humanize' )
def humanize_arrow_date( date ):
    try:
        then = arrow.get(date).to('local')
        now = arrow.utcnow().to('local')
        if then.date() == now.date():
            human = "Today"
        else: 
            human = then.humanize(now)
            if human == "in a day":
                human = "Tomorrow"
    except: 
        human = date

    print(human)
    return human


#############
#
# Functions available to the page code above
#
##############
def get_memos():
    """
    Returns all memos in the database, in a form that
    can be inserted directly in the 'session' object.
    """
    records = []
    for record in collection.find( { "type": "dated_memo" } ):
        record['date'] = arrow.get(record['date']).isoformat()

        # stringifies ID so that it may be used for the 
        # deltion callback in the rendered page- regular
        # ID types do not play well with flask.jsonify().
        record['_id'] = str(record['_id'])
        records.append(record)
    records.sort(key=lambda m: arrow.get(m['date']))
    return records 


if __name__ == "__main__":
    app.debug=CONFIG.DEBUG
    app.logger.setLevel(logging.DEBUG)
    app.run(port=CONFIG.PORT,host="0.0.0.0")

    
