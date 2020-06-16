# ----------------------------------------------------------------------------#
# Imports
# ----------------------------------------------------------------------------#

import json
from itertools import groupby
from operator import attrgetter
from sys import stderr

import dateutil.parser
import babel
import babel.dates
import pytz
from flask import Flask, render_template, request, Response, flash, redirect, url_for
from flask_migrate import Migrate
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
import logging
from logging import Formatter, FileHandler
from flask_wtf import Form
from sqlalchemy import func

from forms import *

# ----------------------------------------------------------------------------#
# App Config.
# ----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
db = SQLAlchemy(app)
migrate = Migrate(app, db)


# ----------------------------------------------------------------------------#
# Models.
# ----------------------------------------------------------------------------#

class Venue(db.Model):
    __tablename__ = 'Venue'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    address = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    genres = db.Column(db.String(120))
    website = db.Column(db.String(120))
    seeking_talent = db.Column(db.Boolean)
    seeking_description = db.Column(db.String)
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))

    shows = db.relationship('Show', backref='venue')


class Artist(db.Model):
    __tablename__ = 'Artist'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    genres = db.Column(db.String(120))
    website = db.Column(db.String(120))
    seeking_venue = db.Column(db.Boolean)
    seeking_description = db.Column(db.String)
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))

    shows = db.relationship('Show', backref='artist')


class Show(db.Model):
    __tablename__ = 'Show'

    venue_id = db.Column(db.Integer, db.ForeignKey('Venue.id'), primary_key=True)
    artist_id = db.Column(db.Integer, db.ForeignKey('Artist.id'), primary_key=True)
    start_time = db.Column(db.String(120), primary_key=True)


# ----------------------------------------------------------------------------#
# Filters.
# ----------------------------------------------------------------------------#

def format_datetime(value, format='medium'):
    date = dateutil.parser.parse(value)
    if format == 'full':
        format = "EEEE MMMM, d, y 'at' h:mma"
    elif format == 'medium':
        format = "EE MM, dd, y h:mma"
    return babel.dates.format_datetime(date, format, locale='en_US')


app.jinja_env.filters['datetime'] = format_datetime


# ----------------------------------------------------------------------------#
# Controllers.
# ----------------------------------------------------------------------------#

@app.route('/')
def index():
    return render_template('pages/home.html')


#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():
    def data_from_grouped_venue(item):
        return {
            "state": item[0][0],
            "city": item[0][1],
            "venues": [{
                "id": venue.id,
                "name": venue.name,
                "num_upcoming_shows": len(get_upcoming_shows(venue.shows))
            } for venue in item[1]]
        }

    all_venues = Venue.query.all()

    sorted_venues = sorted(sorted(all_venues, key=attrgetter('city')), key=attrgetter('state'))
    grouped_venues = groupby(sorted_venues, key=attrgetter('state', 'city'))

    data = [data_from_grouped_venue(item) for item in grouped_venues]

    return render_template('pages/venues.html', areas=data)


@app.route('/venues/search', methods=['POST'])
def search_venues():
    search = request.form.get('search_term')
    venues = Venue.query.filter(func.lower(Venue.name).like(f"%{search.lower()}%")).all()

    response = {
        "count": len(venues),
        "data": [{
            "id": venue.id,
            "name": venue.name,
            "num_upcoming_shows": len(get_upcoming_shows(venue.shows)),
        } for venue in venues]
    }
    return render_template('pages/search_venues.html', results=response,
                           search_term=request.form.get('search_term', ''))


@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
    venue = Venue.query.get(venue_id)

    if venue is None:
        return render_template('errors/404.html')

    past_shows = get_past_shows(venue.shows)
    upcoming_shows = get_upcoming_shows(venue.shows)

    data = {
        "id": venue.id,
        "name": venue.name,
        "genres": json.loads(venue.genres),
        "address": venue.address,
        "city": venue.city,
        "state": venue.state,
        "phone": venue.phone,
        "website": venue.website,
        "facebook_link": venue.facebook_link,
        "seeking_talent": venue.seeking_talent,
        "seeking_description": venue.seeking_description,
        "image_link": venue.image_link,
        "past_shows": [{
            "artist_id": show.artist_id,
            "artist_name": show.artist.name,
            "artist_image_link": show.artist.image_link,
            "start_time": show.start_time
        } for show in past_shows],
        "upcoming_shows": [{
            "artist_id": show.artist_id,
            "artist_name": show.artist.name,
            "artist_image_link": show.artist.image_link,
            "start_time": show.start_time
        } for show in upcoming_shows],
        "past_shows_count": len(past_shows),
        "upcoming_shows_count": len(upcoming_shows),
    }

    return render_template('pages/show_venue.html', venue=data)


#  Create Venue
#  ----------------------------------------------------------------

@app.route('/venues/create', methods=['GET'])
def create_venue_form():
    form = VenueForm()
    return render_template('forms/new_venue.html', form=form)


@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
    form = request.form

    name = form.get('name')
    city = form.get('city')
    state = form.get('state')
    address = form.get('address')
    phone = form.get('phone')
    genres = form.getlist('genres')
    facebook_link = form.get('facebook_link')

    venue = Venue(name=name,
                  city=city,
                  state=state,
                  address=address,
                  phone=phone,
                  genres=json.dumps(genres),
                  facebook_link=facebook_link)
    db.session.add(venue)
    try:
        db.session.commit()
        flash('Venue ' + venue.name + ' was successfully listed!')
    except Exception as e:
        print(e, file=stderr)
        db.session.rollback()
        flash('An error occurred. Venue ' + venue.name + ' could not be listed.', category="error")
    finally:
        db.session.close()

    return render_template('pages/home.html')


@app.route('/venues/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
    try:
        Venue.query.filter_by(id=venue_id).delete()
        db.session.commit()
        flash(f"Venue with id {venue_id} was deleted successfully")
    except Exception as e:
        print(e, file=stderr)
        db.session.rollback()
        flash(f"Venue with id {venue_id} could not be deleted", category='error')
        return render_template('errors/500.html')
    finally:
        db.session.close()

    # BONUS CHALLENGE: Implement a button to delete a Venue on a Venue Page, have it so that
    # clicking that button delete it from the db then redirect the user to the homepage
    return redirect(url_for('index'))


#  Artists
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():
    all_artists = Artist.query.all()
    data = [{
        "id": artist.id,
        "name": artist.name
    } for artist in all_artists]

    return render_template('pages/artists.html', artists=data)


@app.route('/artists/search', methods=['POST'])
def search_artists():
    search = request.form.get('search_term')
    artists = Artist.query.filter(func.lower(Artist.name).like(f"%{search.lower()}%")).all()

    response = {
        "count": len(artists),
        "data": [{
            "id": artist.id,
            "name": artist.name,
            "num_upcoming_shows": len(get_upcoming_shows(artist.shows)),
        } for artist in artists]
    }

    return render_template('pages/search_artists.html', results=response,
                           search_term=request.form.get('search_term', ''))


@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
    artist = Artist.query.get(artist_id)

    if artist is None:
        return render_template('errors/404.html')

    past_shows = get_past_shows(artist.shows)
    upcoming_shows = get_upcoming_shows(artist.shows)

    data = {
        "id": artist.id,
        "name": artist.name,
        "genres": json.loads(artist.genres),
        "city": artist.city,
        "state": artist.state,
        "phone": artist.phone,
        "website": artist.website,
        "facebook_link": artist.facebook_link,
        "seeking_venue": artist.seeking_venue,
        "seeking_description": artist.seeking_description,
        "image_link": artist.image_link,
        "past_shows": [{
            "venue_id": show.venue_id,
            "venue_name": show.venue.name,
            "venue_image_link": show.venue.image_link,
            "start_time": show.start_time
        } for show in past_shows],
        "upcoming_shows": [{
            "venue_id": show.venue_id,
            "venue_name": show.venue.name,
            "venue_image_link": show.venue.image_link,
            "start_time": show.start_time
        } for show in upcoming_shows],
        "past_shows_count": len(past_shows),
        "upcoming_shows_count": len(upcoming_shows),
    }

    return render_template('pages/show_artist.html', artist=data)


#  Update
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
    artist = Artist.query.get(artist_id)

    if artist is None:
        return render_template("errors/404.html")

    data = {
        "id": artist.id,
        "name": artist.name,
        "genres": json.loads(artist.genres),
        "city": artist.city,
        "state": artist.state,
        "phone": artist.phone,
        "website": artist.website,
        "facebook_link": artist.facebook_link,
        "seeking_venue": artist.seeking_venue,
        "seeking_description": artist.seeking_description,
        "image_link": artist.image_link
    }
    form = ArtistForm(name=artist.name,
                      city=artist.city,
                      state=artist.state,
                      phone=artist.phone,
                      genres=json.loads(artist.genres),
                      facebook_link=artist.facebook_link)

    return render_template('forms/edit_artist.html', form=form, artist=data)


@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
    form = request.form

    artist = Artist.query.get(artist_id)

    if artist is None:
        return render_template('errors/404.html')

    artist.name = form.get('name')
    artist.city = form.get('city')
    artist.state = form.get('state')
    artist.phone = form.get('phone')
    artist.genres = json.dumps(form.getlist('genres'))
    artist.facebook_link = form.get('facebook_link')

    try:
        db.session.commit()
    except:
        db.session.rollback()
        return render_template('errors/500.html')
    finally:
        db.session.close()

    return redirect(url_for('show_artist', artist_id=artist_id))


@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
    venue = Venue.query.get(venue_id)

    if venue is None:
        return render_template('errors/404.html')

    form = VenueForm(
        name=venue.name,
        city=venue.city,
        state=venue.state,
        address=venue.address,
        phone=venue.phone,
        genres=json.loads(venue.genres),
        facebook_link=venue.facebook_link,
    )
    data = {
        "id": venue.id,
        "name": venue.name,
        "genres": json.loads(venue.genres),
        "address": venue.address,
        "city": venue.city,
        "state": venue.state,
        "phone": venue.phone,
        "website": venue.website,
        "facebook_link": venue.facebook_link,
        "seeking_talent": venue.seeking_talent,
        "seeking_description": venue.seeking_description,
        "image_link": venue.image_link,
    }
    return render_template('forms/edit_venue.html', form=form, venue=data)


@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
    form = request.form

    venue = Venue.query.get(venue_id)

    if venue is None:
        return render_template('errors/404.html')

    venue.name = form.get('name')
    venue.city = form.get('city')
    venue.state = form.get('state')
    venue.address = form.get('address')
    venue.phone = form.get('phone')
    venue.genres = json.dumps(form.getlist('genres'))
    venue.facebook_link = form.get('facebook_link')

    try:
        db.session.commit()
    except:
        db.session.rollback()
        return render_template('errors/500.html')
    finally:
        db.session.close()

    return redirect(url_for('show_venue', venue_id=venue_id))


#  Create Artist
#  ----------------------------------------------------------------

@app.route('/artists/create', methods=['GET'])
def create_artist_form():
    form = ArtistForm()
    return render_template('forms/new_artist.html', form=form)


@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
    form = request.form

    name = form.get('name')
    city = form.get('city')
    state = form.get('state')
    phone = form.get('phone')
    genres = form.getlist('genres')
    facebook_link = form.get('facebook_link')

    artist = Artist(name=name,
                    city=city,
                    state=state,
                    phone=phone,
                    genres=json.dumps(genres),
                    facebook_link=facebook_link)
    try:
        db.session.add(artist)
        db.session.commit()
        flash('Artist ' + artist.name + ' was successfully listed!')
    except:
        db.session.rollback()
        flash('An error occurred. Artist ' + artist.name + ' could not be listed.', category='error')
    finally:
        db.session.close()

    return render_template('pages/home.html')


#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():
    all_shows = Show.query.all()
    data = [{
        "venue_id": show.venue_id,
        "venue_name": show.venue.name,
        "artist_id": show.artist_id,
        "artist_name": show.artist.name,
        "artist_image_link": show.artist.image_link,
        "start_time": show.start_time
    } for show in all_shows]

    return render_template('pages/shows.html', shows=data)


@app.route('/shows/create')
def create_shows():
    # renders form. do not touch.
    form = ShowForm()
    return render_template('forms/new_show.html', form=form)


@app.route('/shows/create', methods=['POST'])
def create_show_submission():
    form = request.form

    artist_id = form.get('artist_id')
    venue_id = form.get('venue_id')
    start_time = form.get('start_time')

    show = Show(venue_id=venue_id, artist_id=artist_id, start_time=start_time)
    try:
        db.session.add(show)
        db.session.commit()
        flash('Show was successfully listed!')
    except Exception as e:
        db.session.rollback()
        flash('An error occurred. Show could not be listed.')
    finally:
        db.session.close()

    return render_template('pages/home.html')


@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404


@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')


# ----------------------------------------------------------------------------#
# Utils.
# ----------------------------------------------------------------------------#
def get_upcoming_shows(shows):
    return list(
        filter(
            lambda show: dateutil.parser.parse(show.start_time) >= datetime.now(pytz.UTC),
            shows
        )
    )


def get_past_shows(shows):
    return list(
        filter(
            lambda show: dateutil.parser.parse(show.start_time) < datetime.now(pytz.UTC),
            shows
        )
    )


# ----------------------------------------------------------------------------#
# Launch.
# ----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
