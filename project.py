from flask import Flask, render_template, request
from flask import redirect, jsonify, url_for, flash
from sqlalchemy import create_engine, asc
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Brand, BrandItem, User
from flask import session as login_session
import random
import string
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests

app = Flask(__name__)

CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Brand Catalog App"


# Connect to Database and create database session
engine = create_engine('sqlite:///catalog.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


# Connect using Google+ authentication
@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and \
       gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current user ' +
                                            'is already connected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the login_session for later use.
    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['email'] = data['email']

    if getUserID(login_session['email']) is None:
        print "creating user!"
        createUser(login_session)
    else:
        print "user exists!"

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    flash("you are now logged in as %s" % login_session['username'])
    print "done!"
    return output


# Disconnect- Revoke a current user's token and reset their login_session
@app.route('/gdisconnect')
def gdisconnect():
    access_token = login_session['access_token']
    print 'In gdisconnect access token is %s', access_token
    print 'User name is: '
    print login_session['username']
    if access_token is None:
        print 'Access Token is None'
        response = make_response(json.dumps('Current user ' +
                                            'not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % \
          login_session['access_token']
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    print 'result is '
    print result
    if result['status'] == '200':
        del login_session['access_token']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        # return response
        return redirect(url_for('showLogin'))
    else:
        response = make_response(json.dumps('Failed to ' +
                                            'revoke token ' +
                                            'for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response


# Create new user
def createUser(login_session):
    newUser = User(name=login_session['username'],
                   email=login_session['email'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


# Get user info by user_id
def getUserInfo(user_id):
    try:
        user = session.query(User).filter_by(id=user_id).one()
        return user
    except:
        return None


# Get user id by email
def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None


# JSON APIs to view Brand Information
@app.route('/brand/<int:brand_id>/items/JSON')
def brandItemsJSON(brand_id):
    brand = session.query(Brand).filter_by(id=brand_id).one()
    items = session.query(BrandItem).filter_by(brand_id=brand_id).all()
    return jsonify(BrandItems=[i.serialize for i in items])


@app.route('/brand/<int:brand_id>/items/<int:item_id>/JSON')
def brandItemJSON(brand_id, item_id):
    Brand_Item = session.query(BrandItem).filter_by(id=item_id).one()
    return jsonify(Brand_Item=Brand_Item.serialize)


@app.route('/brand/JSON')
def brandsJSON():
    brands = session.query(Brand).all()
    return jsonify(brands=[brand.serialize for brand in brands])


# Create anti-forgery state token
@app.route('/login')
def showLogin():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    return render_template('login.html', STATE=state)


# Show all brands
@app.route('/')
@app.route('/brand/')
def showBrands():
    brands = session.query(Brand).order_by(asc(Brand.name))
    return render_template('brands.html', brands=brands)


# Create a new brand
@app.route('/brand/new/', methods=['GET', 'POST'])
def newBrand():
    if 'username' not in login_session:
        flash('Must be login to create a brand!')
        return redirect('/brand')
    if request.method == 'POST':
        newBrand = Brand(name=request.form['name'],
                         user_id=getUserID(login_session['email']))
        session.add(newBrand)
        flash('New Brand %s Successfully Created' % newBrand.name)
        session.commit()
        return redirect(url_for('showBrands'))
    else:
        return render_template('newBrand.html')


# Edit a brand
@app.route('/brand/<int:brand_id>/edit/', methods=['GET', 'POST'])
def editBrand(brand_id):
    if 'username' not in login_session:
        flash('Must be login to edit a brand!')
        return redirect('/brand')
    editedBrand = session.query(Brand).filter_by(id=brand_id).one()
    addedByUser = session.query(User).filter_by(id=editedBrand.user_id).one()
    print "Added by User %s" % addedByUser.email
    if request.method == 'POST' and \
       addedByUser.name == login_session['username']:
        if request.form['name']:
            editedBrand.name = request.form['name']
            flash('Brand Successfully Edited %s' % editedBrand.name)
            return redirect(url_for('showBrands'))
        else:
            flash('Invalid user to edit %s' % editedBrand.name)
            return redirect(url_for('showBrands'))
    else:
        if addedByUser.name != login_session['username']:
            flash('Invalid user to edit %s' % editedBrand.name)
            return redirect(url_for('showBrands'))
        else:
            return render_template('editBrand.html', brand=editedBrand)


# Delete a brand
@app.route('/brand/<int:brand_id>/delete/', methods=['GET', 'POST'])
def deleteBrand(brand_id):
    if 'username' not in login_session:
        flash('Must be login to delete a brand!')
        return redirect('/brand')
    brandToDelete = session.query(Brand).filter_by(id=brand_id).one()
    addedByUser = session.query(User).filter_by(id=brandToDelete.user_id).one()
    if request.method == 'POST' and \
       addedByUser.name == login_session['username']:
        session.delete(brandToDelete)
        flash('%s Successfully Deleted' % brandToDelete.name)
        session.commit()
        return redirect(url_for('showBrands', brand_id=brand_id))
    else:
        if addedByUser.name != login_session['username']:
            flash('Invalid user to delete %s' % brandToDelete.name)
            return redirect(url_for('showBrands'))
        else:
            return render_template('deleteBrand.html', brand=brandToDelete)


# Show brand items
@app.route('/brand/<int:brand_id>/')
@app.route('/brand/<int:brand_id>/items/')
def showItems(brand_id):
    brand = session.query(Brand).filter_by(id=brand_id).one()
    items = session.query(BrandItem).filter_by(brand_id=brand_id).all()
    return render_template('items.html', items=items, brand=brand)


# Create a new brand item
@app.route('/brand/<int:brand_id>/items/new/', methods=['GET', 'POST'])
def newBrandItem(brand_id):
    if 'username' not in login_session:
        flash('Must be login to create a brand item!')
        return redirect('/brand')
    brand = session.query(Brand).filter_by(id=brand_id).one()
    if request.method == 'POST':
        newItem = BrandItem(name=request.form['name'],
                            description=request.form['description'],
                            brand_id=brand_id,
                            user_id=getUserID(login_session['email']))
        session.add(newItem)
        session.commit()
        flash('New Brand %s Item Successfully Created' % (newItem.name))
        return redirect(url_for('showItems', brand_id=brand_id))
    else:
        return render_template('newbranditem.html', brand_id=brand_id)


# Edit a brand item
@app.route('/brand/<int:brand_id>/items/<int:item_id>/edit',
           methods=['GET', 'POST'])
def editBrandItem(brand_id, item_id):
    if 'username' not in login_session:
        flash('Must be login to edit a brand item!')
        return redirect('/brand')
    editedItem = session.query(BrandItem).filter_by(id=item_id).one()
    brand = session.query(Brand).filter_by(id=brand_id).one()
    addedByUser = session.query(User).filter_by(id=editedItem.user_id).one()
    if request.method == 'POST' and \
       addedByUser.name == login_session['username']:
        if request.form['name']:
            editedItem.name = request.form['name']
        if request.form['description']:
            editedItem.description = request.form['description']
            session.add(editedItem)
            session.commit()
            flash('Brand Item Successfully Edited')
            return redirect(url_for('showItems', brand_id=brand_id))
    else:
        if addedByUser.name != login_session['username']:
            flash('Invalid user to edit %s' % editedItem.name)
            return redirect(url_for('showBrands'))
        else:
            return render_template('editbranditem.html', brand_id=brand_id,
                                   item_id=item_id, item=editedItem)


# Delete a brand item
@app.route('/brand/<int:brand_id>/items/<int:item_id>/delete',
           methods=['GET', 'POST'])
def deleteBrandItem(brand_id, item_id):
    if 'username' not in login_session:
        flash('Must be login to delete a brand item!')
        return redirect('/brand')
    brand = session.query(Brand).filter_by(id=brand_id).one()
    itemToDelete = session.query(BrandItem).filter_by(id=item_id).one()
    addedByUser = session.query(User).filter_by(id=itemToDelete.user_id).one()
    if request.method == 'POST' and \
       addedByUser.name == login_session['username']:
        session.delete(itemToDelete)
        session.commit()
        flash('Brand Item Successfully Deleted')
        return redirect(url_for('showItems', brand_id=brand_id))
    else:
        if addedByUser.name != login_session['username']:
            flash('Invalid user to delete %s' % itemToDelete.name)
            return redirect(url_for('showBrands'))
        else:
            return render_template('deleteBrandItem.html', item=itemToDelete)


if __name__ == '__main__':
    app.secret_key = 'secret'
    app.debug = True
    app.run(host='0.0.0.0', port=5000)
