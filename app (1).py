from flask import Flask, render_template, request, redirect, url_for, session
# Other necessary imports
from flask_googlemaps import GoogleMaps
from flask_googlemaps import Map
from googlemaps import convert
import pymongo
import googlemaps
import random
import uuid

client = pymongo.MongoClient(
    "mongodb+srv://christabel:<password>@clusterp1.jlbwrmx.mongodb.net/?retryWrites=true&w=majority&appName=ClusterP1"
)

db = client.test
collection = db.coordinates

app = Flask(__name__, template_folder="templates")
app.secret_key = 'notavailable' 
app.config['SESSION_TYPE'] = 'filesystem'

Session(app)

#new# Use environment variable for MongoDB connection string
mongo_uri = os.getenv("MONGO_URI")
client = pymongo.MongoClient(mongo_uri)


key = "not available" 
GoogleMaps(
    app,
    key=key
)


def geocode(address=None, components=None, bounds=None, region=None,
            language=None):
    """
    Geocoding is the process of converting addresses
    (like ``"1600 Amphitheatre Parkway, Mountain View, CA"``) into geographic
    coordinates (like latitude 37.423021 and longitude -122.083739), which you
    can use to place markers or position the map.
    :param address: The address to geocode.
    :type address: string
    :param components: A component filter for which you wish to obtain a
        geocode, for example: ``{'administrative_area': 'TX','country': 'US'}``
    :type components: dict
    :param bounds: The bounding box of the viewport within which to bias geocode
        results more prominently.
    :type bounds: string or dict with northeast and southwest keys.
    :param region: The region code, specified as a ccTLD ("top-level domain")
        two-character value.
    :type region: string
    :param language: The language in which to return results.
    :type language: string
    :rtype: list of geocoding results.
    """

    client = googlemaps.Client(key)

    params = {}

    if address:
        params["address"] = address

    if components:
        params["components"] = convert.components(components)

    if bounds:
        params["bounds"] = convert.bounds(bounds)

    if region:
        params["region"] = region

    if language:
        params["language"] = language

    return client._request("/maps/api/geocode/json", params).get("results", [])


@app.route("/")
def index():
    session["state"] = str(uuid.uuid4())
    return render_template('index.html')


@app.route("/actions")
def actions():
    return render_template('actions.html')


@app.route("/rally_form")
def rally_form():
    return render_template('rally_form.html')


@app.route('/new_rally', methods=['POST'])
def new_rally():
    title = request.form['title']
    location = request.form['location']
    response = geocode(address=location)
    if not response:
        return redirect(url_for('index'))
    else:
        response = response[0]
    session['location'] = location
    latitude = response['geometry']['location']['lat']
    longitude = response['geometry']['location']['lng']
    description = request.form['description']
    date = request.form['date']
    start_time = request.form['startTime']
    end_time = request.form['endTime']
    url = request.form['url']
    my_cursor = collection.find()
    for item in my_cursor:
        if item['lat'] == latitude and item['lng'] == longitude:
            longitude += random.random()*0.001
            latitude += random.random()*0.001

    _id = collection.count() + 1
    collection.insert_one({
        "_id": _id,
        "title": title,
        "lat": latitude,
        "lng": longitude,
        "confirm_count": 0,
        "date": date,
        "start_time": start_time,
        "end_time": end_time,
        "bio": description,
        "url": url
    })
    return redirect(url_for('map_view'))


@app.route("/enterCity")
def enterCity():
    return render_template('enterCity.html')


@app.route("/nearMe", methods=['GET', 'POST'])
def map_view():
    if not session.get("location"):
        return redirect(url_for("index"))
    location = session['location']
    response = geocode(address=location, region='Canada')
    if not response:
        return redirect(url_for('index'))
    else:
        response = response[0]
    resp_len = len(response['address_components'])
    location = response['address_components'][int(resp_len / 2 - 2)]['long_name']
    search_lat = (response['geometry']['location']['lat'])
    search_lng = (response['geometry']['location']['lng'])

    markers = [{
        'icon': '//maps.google.com/mapfiles/ms/icons/red-dot.png',
        'lat': search_lat,
        'lng': search_lng
    }]

    my_cursor = collection.find()
    for item in my_cursor:
        title = "<p><strong>{}</strong></p>"
        par = "<p>{}</p>"
        link = "<a href={}>Learn More</a>"
        markers.append({
            'icon': '//maps.google.com/mapfiles/ms/icons/green-dot.png',
            'lat': item['lat'],
            'lng': item['lng'],
            'infobox': title.format(item['title']) +
                       par.format(item['bio']) +
                       par.format(par.format('Date: ' + item['date'])) +
                       par.format(par.format('Time: ' + item['start_time'] + '-' + item['end_time'])) +
                       par.format(link.format(item['url']))
        })

    circlemap = Map(
        identifier="circlemap",
        varname="circlemap",
        lat=search_lat,
        lng=search_lng,
        markers=markers,
        style=(
            "height:500px;"
            "width:100%;"
            "align: center;"
            "display: block;"
            "margin-left: auto;"
            "margin-right: auto;"
        ),
    )

    return render_template(
        'nearMe.html',
        circlemap=circlemap,
        GOOGLEMAPS_KEY=request.args.get('apikey'),
        location=location,
    )


@app.route('/get_city', methods=['POST'])
def get_city():
    city = request.form['city']
    session['location'] = city
    return redirect(url_for('map_view'))


@app.route('/<path:path>')
def notFound(path):
    return render_template('404.html')


if __name__ == "__main__":
    # app.run(debug=True, use_reloader=True)
    app.run(debug=True, ssl_context='adhoc')
