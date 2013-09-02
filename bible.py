#imports
# -*- coding: utf-8 -*-\
import sqlite3
from contextlib import closing
from flask import Flask, request, session, g, redirect, url_for, abort, render_template, flash, jsonify
from flaskext.mongoalchemy import MongoAlchemy


#app configuration
DATABASE = 'db/bible-br.db'
DEBUG = True
SECRET_KEY = 'dev'
USERNAME = 'admin'
PASSWORD = 'admin'

app = Flask(__name__)
#app.config.from_envvar('BIBLE_SETTINGS',silent=True)
#mongoDB config
app.config['MONGOALCHEMY_DATABASE'] = 'hilights'
db_mongo = MongoAlchemy(app)
app.config.from_object(__name__)

#mongoDB classes
class Hilight(db_mongo.Document):
    book_api_name = db_mongo.StringField()
    refs = db_mongo.SetField(db_mongo.StringField())

class Comment(db_mongo.Document):
    book_api_name = db_mongo.StringField()
    chapter = db_mongo.IntField()
    verses = db_mongo.KVField(db_mongo.IntField(),db_mongo.StringField(), default_empty = True)
    
#db functions
def connect_db():
    return sqlite3.connect(app.config['DATABASE'])

def init_db():
    with closing(connect_db()) as db:
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()

@app.before_request
def before_request():
    g.db = connect_db()
    g.db.text_factory = str

@app.teardown_request
def teardown_request(exception):
    db = getattr(g, 'db', None)
    if db is not None:
        db.close()

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = connect_db()
    db.text_factory = str
    return db
        
def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv
        


#app
@app.route('/show_chapter/<book>/<int:chapter>')
def show_chapter(book,chapter):
    book_id,book_name = query_db('select id,book_name from books where book_api_name=?',[book],one=True)
    result = query_db('select verse_num,verse,id from texts where id_book=? and chapter_num=?',[book_id,chapter])
    verses = [dict(verse_num=row[0],verse=row[1],id=row[2]) for row in result]

    #get the next chapter - it needs to verify wether it belongs to another book or not
    #it verifies to which book the next verse belongs getting the next verse id of the verses table
    next_chapter = get_next_prev_chapter(verses[-1]['id'],1)
    url_next= url_for('show_chapter',book=next_chapter['book'],chapter=next_chapter['chapter'])

    #the same for the previous chapter
    prev_chapter = get_next_prev_chapter(verses[0]['id'],-1)
    url_prev= url_for('show_chapter',book=prev_chapter['book'],chapter=prev_chapter['chapter'])

    #query for the user's hilights
    hilights = get_hilights(book)
    #if there's any hilighted text, mark it, filtering the correct chapter
    if hilights:
        h_verses = get_hilighted_verses(hilights,chapter)
        if DEBUG:
            print 'h_verses: '
            print  h_verses
    else:
        h_verses = set([])
        
    return render_template('show_chapter.html',verses=verses,chapter=chapter,book_name=book_name,url_next=url_next,url_prev=url_prev,hilights=h_verses)

def get_next_prev_chapter(verse_id,next_prev):
    verse_id += next_prev
    book_id,chapter = query_db('select id_book,chapter_num from texts where id=?',[verse_id],one=True)
    book, = query_db('select book_api_name from books where id=?',[book_id],one=True)
    return dict(book=book,chapter=chapter)

#needs review and model creation, before tests
@app.route('/comment')
def save_comment():
    chapter = request.args.get('chapter')
    verse = request.args.get('verse')
    book = request.args.get('book')
    comment = request.args.get('comment')
    if DEBUG:
        print ref, book, comment
    comments = get_comments(book,chapter)
    if not comments:
        _verse = mongo_db.KVField(mongo_db.IntField(),mongo_db.StringField())
        _verse.wrap({verse : comment})
        comments = Comment(book_api_name=book,chapter=chapter,verses = _verse)
        comments.save()
        return jsonify(result=True)
    else:
        comments.verses[verse] = comment
        comment.save()
        return jsonify(result=True)
    return jsonify(result=False)

@app.route('/hilight')
def save_hilight():
    ref = request.args.get('ref')
    book = request.args.get('book')
    if DEBUG:
        print ref, book
    hilight = get_hilights(book)
    if not hilight:
        hilight = Hilight(book_api_name=book,refs=set([ref]))
        hilight.save()
        return jsonify(result=True)
    else:
        hilight.refs.add(ref)
        hilight.save()
        return jsonify(result=True)
    return jsonify(result=False)


#get all the hilights for that specific book
def get_hilights(book):
    return Hilight.query.filter(Hilight.book_api_name == book).first()    

#get all the hilights for that specific book
def get_comments(book,chapter):
    return Comment.query.filter(Comment.book_api_name == book,Comment.chapter == chapter).first()    

#filter the hilights for the chapter in the current view
# TODO -- cache functions
def get_hilighted_verses(hilights,chapter):
    return  hilights.refs

if __name__ == '__main__':
    app.run(host='0.0.0.0')

