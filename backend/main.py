from datetime import date
import csv
import io
import json
import re
import sqlite3

from dicttoxml import dicttoxml
from flask import Flask, g, request, make_response, Response
from flask_cors import CORS
from wordcloud import WordCloud

STOPWORDS = ['de', 'a', 'o', 'que', 'e', 'do', 'da', 'em', 'um', 'para', 'é', 'com', 'não', 'uma', 'os', 'no', 'se', 'na', 'por', 'mais', 'as', 'dos', 'como', 'mas', 'foi', 'ao', 'ele', 'das', 'tem', 'à', 'seu', 'sua', 'ou', 'ser', 'quando', 'muito', 'há', 'nos', 'já', 'está', 'eu', 'também', 'só', 'pelo', 'pela', 'até', 'isso', 'ela', 'entre', 'era', 'depois', 'sem', 'mesmo', 'aos', 'ter', 'seus', 'quem', 'nas', 'me', 'esse', 'eles', 'estão', 'você', 'tinha', 'foram', 'essa', 'num', 'nem', 'suas', 'meu', 'às', 'minha', 'têm', 'numa', 'pelos', 'elas', 'havia', 'seja', 'qual', 'será', 'nós', 'tenho', 'lhe', 'deles', 'essas', 'esses', 'pelas', 'este', 'fosse', 'dele', 'tu', 'te', 'vocês', 'vos', 'lhes', 'meus', 'minhas', 'teu', 'tua', 'teus', 'tuas', 'nosso', 'nossa', 'nossos', 'nossas', 'dela', 'delas', 'esta', 'estes', 'estas', 'aquele', 'aquela', 'aqueles', 'aquelas', 'isto', 'aquilo', 'estou', 'está', 'estamos', 'estão', 'estive', 'esteve', 'estivemos', 'estiveram', 'estava', 'estávamos', 'estavam', 'estivera', 'estivéramos', 'esteja', 'estejamos', 'estejam', 'estivesse', 'estivéssemos', 'estivessem', 'estiver', 'estivermos', 'estiverem', 'hei', 'há', 'havemos', 'hão', 'houve', 'houvemos', 'houveram', 'houvera', 'houvéramos', 'haja', 'hajamos', 'hajam', 'houvesse', 'houvéssemos', 'houvessem', 'houver', 'houvermos', 'houverem', 'houverei', 'houverá', 'houveremos', 'houverão', 'houveria', 'houveríamos', 'houveriam', 'sou', 'somos', 'são', 'era', 'éramos', 'eram', 'fui', 'foi', 'fomos', 'foram', 'fora', 'fôramos', 'seja', 'sejamos', 'sejam', 'fosse', 'fôssemos', 'fossem', 'for', 'formos', 'forem', 'serei', 'será', 'seremos', 'serão', 'seria', 'seríamos', 'seriam', 'tenho', 'tem', 'temos', 'tém', 'tinha', 'tínhamos', 'tinham', 'tive', 'teve', 'tivemos', 'tiveram', 'tivera', 'tivéramos', 'tenha', 'tenhamos', 'tenham', 'tivesse', 'tivéssemos', 'tivessem', 'tiver', 'tivermos', 'tiverem', 'terei', 'terá', 'teremos', 'terão', 'teria', 'teríamos', 'teriam']
DATABASE_FILENAME = 'database.db'
APP = Flask(__name__)
CORS(APP, supports_credentials=True)


def get_database():
    DATABASE = getattr(g, '_database', None)
    if DATABASE is None:
        DATABASE = g._database = sqlite3.connect(DATABASE_FILENAME)
    return DATABASE


@APP.teardown_appcontext
def close_connection(_):
    DATABASE = getattr(g, '_database', None)
    if DATABASE is not None:
        DATABASE.close()


@APP.route('/add/page', methods=['POST'])
def add_page():
    DB_CUR = get_database().cursor()
    DB_CUR.execute(f'INSERT INTO pages VALUES ("{request.form["userid"]}", "{request.form["username"]}", {request.form["followers"]})')
    get_database().commit()
    return {'error': 0}


@APP.route('/add/tweet', methods=['POST'])
def add_tweet():
    DB_CUR = get_database().cursor()
    FMT_TWEET = re.sub(' +', ' ', request.form["text"].replace('\n', ' ').replace('"', '').strip())

    DB_CUR.execute(f'INSERT INTO tweets (text, userid, date_day, date_month, date_year, positive_feeling) VALUES ("{FMT_TWEET}", "{request.form["userid"]}", "{request.form["date_day"]}", "{request.form["date_month"]}", "{request.form["date_year"]}", "{request.form["positive_feeling"]}")')
    get_database().commit()
    return {'error': 0}


@APP.route('/view/page', methods=['POST'])
def view_page():
    DB_CUR = get_database().cursor()
    PAGE = list(DB_CUR.execute(f'SELECT userid, username, followers FROM pages WHERE userid=="{request.form["userid"]}"'))[0]
    SAVED_TWEETS = list(DB_CUR.execute(f'SELECT COUNT(*) FROM tweets WHERE userid=="{request.form["userid"]}"'))[0][0]
    return {'error': 0, 'response': {'userid': PAGE[0], 'username': PAGE[1], 'followers': PAGE[2], 'saved_tweets': SAVED_TWEETS}}


@APP.route('/view/tweet', methods=['POST'])
def view_tweet():
    DB_CUR = get_database().cursor()
    return {'error': 0, 'response': {'tweets': [{'userid': x[0], 'text':x[1], 'date_day':x[2], 'date_month':x[3], 'date_year':x[4], 'positive_feeling':x[5]} for x in list(DB_CUR.execute(f'SELECT userid, text, date_day, date_month, date_year, positive_feeling FROM tweets'))]}}


@APP.route('/word_ocurrence', methods=['POST'])
def word_ocurrence():
    DB_CUR = get_database().cursor()
    START_DATE = date(int(request.form['start_year']), int(request.form['start_month']), int(request.form['start_day']))
    END_DATE = date(int(request.form['end_year']), int(request.form['end_month']), int(request.form['end_day']))
    text = ""

    for x in DB_CUR.execute(f'SELECT text, date_year, date_month, date_day FROM tweets WHERE userid=="{request.form["userid"]}"'):
        TWEET_DATE = date(x[1], x[2], x[3])
        if START_DATE <= TWEET_DATE and END_DATE >= TWEET_DATE:
            text += x[0] + ' '

    counts = dict()
    words = text.split()

    for word in words:
        if word in counts:
            counts[word] += 1
        else:
            counts[word] = 1

    return {'error': 0, 'response': {'word_ocurrence': sorted([{'word': x[0], 'ocurrences': x[1]} for x in counts.items() if x[0].lower() not in STOPWORDS], key=lambda x: x['ocurrences'], reverse=True)[:20]}}


@APP.route('/positive_feeling_percentage', methods=['POST'])
def positive_feeling_percentage():
    DB_CUR = get_database().cursor()
    START_DATE = date(int(request.form['start_year']), int(request.form['start_month']), int(request.form['start_day']))
    END_DATE = date(int(request.form['end_year']), int(request.form['end_month']), int(request.form['end_day']))
    QUERY = list(DB_CUR.execute(f'SELECT positive_feeling, date_year, date_month, date_day FROM tweets WHERE userid=="{request.form["userid"]}"'))
    negative = 0
    neutral = 0
    positive = 0

    for x in QUERY:
        TWEET_DATE = date(x[1], x[2], x[3])
        if START_DATE <= TWEET_DATE and END_DATE >= TWEET_DATE:
            if x[0] == -1:
                negative += 1
            elif x[1] == 0:
                neutral += 1
            else:
                positive += 1

    LENGHT = len(QUERY) if len(QUERY) != 0 else 1

    negative = negative / LENGHT * 100
    neutral = neutral / LENGHT * 100
    positive = positive / LENGHT * 100
    return {'error': 0, 'response': {'negative_percentage': negative, 'neutral_percentage': neutral, 'positive_percentage': positive}}


@APP.route('/csv/all_pages', methods=['GET'])
def csv__all_pages():
    DB_CUR = get_database().cursor()
    dest = io.StringIO()
    writer = csv.writer(dest)
    writer.writerow(['userid', 'username', 'followers'])

    for i in list(DB_CUR.execute('SELECT userid, username, followers FROM pages')):
        writer.writerow(i)

    output = make_response(dest.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=bubblegun_all_pages.csv"
    output.headers["Content-type"] = "text/csv"
    return output


@APP.route('/csv/all_tweets', methods=['GET'])
def csv__all_tweets():
    DB_CUR = get_database().cursor()
    dest = io.StringIO()
    writer = csv.writer(dest)
    writer.writerow(['text', 'date_day', 'date_month', 'date_year', 'positive_feeling', 'userid', 'username', 'followers'])

    for i in list(DB_CUR.execute('SELECT text, date_day, date_month, date_year, positive_feeling, tweets.userid, username, followers FROM tweets INNER JOIN pages ON tweets.userid = pages.userid')):
        writer.writerow(i)

    output = make_response(dest.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=bubblegun_all_tweets.csv"
    output.headers["Content-type"] = "text/csv"
    return output


@APP.route('/xml/all_pages', methods=['GET'])
def xml__all_pages():
    DB_CUR = get_database().cursor()
    raw_xml = dicttoxml([{'userid': x[0], 'username': x[1], 'followers': x[2]} for x in list(DB_CUR.execute('SELECT userid, username, followers FROM pages'))], custom_root='pages', attr_type=False)

    output = make_response(raw_xml)
    output.headers["Content-Disposition"] = "attachment; filename=bubblegun_all_pages.xml"
    output.headers["Content-type"] = "text/xml"
    return output


@APP.route('/xml/all_tweets', methods=['GET'])
def xml__all_tweets():
    DB_CUR = get_database().cursor()
    raw_xml = dicttoxml([{'text': x[0], 'date_day':x[1], 'date_month':x[2], 'date_year':x[3], 'positive_feeling':x[4], 'userid':x[5], 'username':x[6], 'followers':x[7]} for x in list(DB_CUR.execute('SELECT text, date_day, date_month, date_year, positive_feeling, tweets.userid, username, followers FROM tweets INNER JOIN pages ON tweets.userid = pages.userid'))], custom_root='tweets', attr_type=False)

    output = make_response(raw_xml)
    output.headers["Content-Disposition"] = "attachment; filename=bubblegun_all_tweets.xml"
    output.headers["Content-type"] = "text/xml"
    return output


@APP.route('/json/all_pages', methods=['GET'])
def json__all_pages():
    DB_CUR = get_database().cursor()
    raw_json = json.dumps([{'userid': x[0], 'username': x[1], 'followers': x[2]} for x in list(DB_CUR.execute('SELECT userid, username, followers FROM pages'))])

    output = make_response(raw_json)
    output.headers["Content-Disposition"] = "attachment; filename=bubblegun_all_pages.json"
    output.headers["Content-type"] = "text/json"
    return output


@APP.route('/json/all_tweets', methods=['GET'])
def json__all_tweets():
    DB_CUR = get_database().cursor()
    raw_json = json.dumps([{'text': x[0], 'date_day':x[1], 'date_month':x[2], 'date_year':x[3], 'positive_feeling':x[4], 'userid':x[5], 'username':x[6], 'followers':x[7]} for x in list(DB_CUR.execute('SELECT text, date_day, date_month, date_year, positive_feeling, tweets.userid, username, followers FROM tweets INNER JOIN pages ON tweets.userid = pages.userid'))])

    output = make_response(raw_json)
    output.headers["Content-Disposition"] = "attachment; filename=bubblegun_all_tweets.json"
    output.headers["Content-type"] = "text/json"
    return output


@APP.route('/wordcloud', methods=['POST'])
def wordcloud():

    DB_CUR = get_database().cursor()
    img = io.BytesIO()

    START_DATE = date(int(request.form['start_year']), int(request.form['start_month']), int(request.form['start_day']))
    END_DATE = date(int(request.form['end_year']), int(request.form['end_month']), int(request.form['end_day']))
    text = ""

    for x in DB_CUR.execute(f'SELECT text, date_year, date_month, date_day FROM tweets WHERE userid=="{request.form["userid"]}"'):
        TWEET_DATE = date(x[1], x[2], x[3])
        if START_DATE <= TWEET_DATE and END_DATE >= TWEET_DATE:
            text += x[0] + ' '

    wordcloud = WordCloud(stopwords=STOPWORDS, background_color="black", width=1600, height=800).generate(text)
    wordcloud.to_image().save(img, 'PNG')

    return Response(img.getvalue(), mimetype='image/png')


if __name__ == '__main__':
    APP.run('localhost', port=8080)
