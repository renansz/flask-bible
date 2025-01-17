#imports
# -*- coding: utf-8 -*-\
import sqlite3
from contextlib import closing
from flask import Flask, request, session, g, redirect, url_for, abort, render_template, flash

#app configuration
DATABASE = 'db/bible-br.db'
DEBUG = True
SECRET_KEY = 'dev'
USERNAME = 'admin'
PASSWORD = 'admin'

app = Flask(__name__)
#app.config.from_envvar('BIBLE_SETTINGS',silent=True)
app.config.from_object(__name__)

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
    #it verifies to which book the next verse below getting the next verse id of our database
    next_chapter = get_next_prev_chapter(verses[-1]['id'],1)
    url_next= url_for('show_chapter',book=next_chapter['book'],chapter=next_chapter['chapter'])
    #the same for the previous chapter
    prev_chapter = get_next_prev_chapter(verses[0]['id'],-1)
    url_prev= url_for('show_chapter',book=prev_chapter['book'],chapter=prev_chapter['chapter'])
    
    return render_template('show_chapter.html',verses=verses,chapter=chapter,book_name=book_name,url_next=url_next,url_prev=url_prev)

def get_next_prev_chapter(last_verse_id,next_prev):
    last_verse_id += next_prev
    book_id,chapter = query_db('select id_book,chapter_num from texts where id=?',[last_verse_id],one=True)
    book, = query_db('select book_api_name from books where id=?',[book_id],one=True)
    return dict(book=book,chapter=chapter)


if __name__ == '__main__':
    app.run(host='0.0.0.0')

