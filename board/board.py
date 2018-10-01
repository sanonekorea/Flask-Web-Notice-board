from flask import Flask,request,g,render_template,session,redirect,url_for
import sqlite3
import hashlib
import os
from werkzeug import secure_filename
DATABASE = './db/board.db'
app = Flask(__name__)
app.secret_key = "san91"

##database##

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g,'_database',None)
    if db is not None:
        db.close()

def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

def init_db_first():
    with app.app_context():
        db = get_db()
        with app.open_resource('schema/schema1.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()

def init_db_second():
    with app.app_context():
        db = get_db()
        with app.open_resource('schema/schema2.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()

def init_db_third():
    with app.app_context():
        db = get_db()
        with app.open_resource('schema/schema3.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()

##notice board##

def search_table():
    sql = "select rowid,* from board order by rowid desc"
    db = get_db()
    rv = db.execute(sql)
    res = rv.fetchall()
    return res

@app.route('/', methods=["GET","POST"])
def index():
    if session.get('user_id', None) != None:
        gss = session['user_id']
        data = search_table()
        try:
            idx = data[0][0]
            return render_template('index.html', gss=gss, data=data, idx=idx)
        except IndexError:
            return render_template('index.html', gss=gss, data=None, idx=0)
    else:
        data = search_table()
        try:
            idx = data[0][0]
            return render_template('index.html', data=data, idx=idx)
        except IndexError:
            return render_template('index.html', data=None, idx=0)

@app.route('/posting', methods=['GET','POST'])
def posting():
    if session.get('user_id',None) != None:
        if request.method == "GET":
            return render_template('posting.html')
        elif request.method == "POST":
            writer = session.get('user_id')
            content = request.form.get('content')
            title = request.form.get('title')
            date = get_date()
            if len(title) != 0:
                sql = "insert into board (title, date, writer, content) values ('%s', '%s','%s','%s')" %(title, date, writer, content)
                db = get_db()
                rv = db.execute(sql)
                res = db.commit()
                idx = get_idx(writer,title,date)
                upload_file(idx)
                return redirect(url_for('index'))
            else:
                return '''<script>
                        alert('You have to input title');
                        history.go(-1);
                        </script>'''
    else:
        return redirect(url_for('login'))

def get_idx(writer,title,date):
    sql = "select rowid from board where writer='%s' and title='%s' and date='%s' limit 1" %(writer,title,date)
    db = get_db()
    rv = db.execute(sql)
    res = rv.fetchone()
    return res[0]

def get_date():
    sql = "select current_timestamp"
    db = get_db()
    rv = db.execute(sql)
    res = rv.fetchone()
    return res[0]

@app.route('/view/<idx>')
def view_post(idx):
    sql = "select rowid,* from board where rowid=%d" %(int(idx))
    db = get_db()
    rv = db.execute(sql)
    res = rv.fetchone()
    idx = res[0]
    title = res[1]
    date = res[2]
    writer= res[3]
    content = res[4]
    fin = res[5]
    res = get_comment(idx)
    a = len(res)
    if session.get('user_id',None) != None:
        if request.method == "GET":
            gss = session['user_id']
            return render_template('view.html',gss=gss,title=title,content=content,writer=writer,date=date,idx=idx,res=res,a=a,fin=fin)
        elif request.method == "POST":
            return render_template('view.html',gss=gss,title=title,content=content,writer=writer,date=date,idx=idx,res=res,a=a,fin=fin)
    else:
        return render_template('view.html',title=title,content=content,writer=writer,date=date,idx=idx,gss=None,res=res,a=a,fin=fin)

def get_comment(idx):
    sql = "select rowid,* from comment where idx = %d" %(int(idx))
    db = get_db()
    rv = db.execute(sql)
    res = rv.fetchall()
    return res

def find_content(idx):
    sql = "select rowid,* from board where rowid=%d" %(idx)
    db = get_db()
    rv = db.execute(sql)
    res = rv.fetchone()
    return res[0]

@app.route('/modipost/<idx>', methods=['GET','POST'])
def modify_post(idx):
    if session.get('user_id', None) != None:
        gss = checkme(int(idx))
        if gss == session['user_id']:
            if request.method == "GET":
                data = find_content(int(idx))
                return render_template('modpost.html',idx=idx)
            elif request.method == "POST":
                title = request.form.get('title')
                content = request.form.get('content')
                if len(title) == 0 or len(content) == 0:
                    return '<script>history.go(-2)</script>'
                else:
                    date = get_date()
                    sql = "update board set title='%s',content='%s',date='%s' where rowid=%d" %(title,content,date,int(idx))
                    db = get_db()
                    rv = db.execute(sql)
                    res = db.commit()
                    return redirect(url_for('index'))
        else:
            return '''<script>alert('Writer only!');history.go(-1);</script>'''
    else:
        return '''<script>alert('Login First!');history.go(-1);</script>'''

@app.route('/delete/<idx>', methods=['GET','POST'])
def delete_post(idx):
    if session.get('user_id',None) != None:
        gss = checkme(int(idx))
        if gss == session['user_id']:
            path = find_filename(idx)
            if path is None:
                pass
            else:
                try:
                    os.remove(path)
                    os.removedirs('./uploads/'+str(idx))
                except OSError:
                    pass
            sql = 'delete from board where rowid=%d'%(int(idx))
            db = get_db()
            rv = db.execute(sql)
            db.commit()
            return redirect(url_for('index'))
        else:
            return '''<script>alert('Writer only!');history.go(-1);</script> '''
    else:
        return '''<script>alert('Login First!');history.go(-1);</script> '''

def checkme(idx):
   sql = "select writer from board where rowid=%d" %(idx)
   db =get_db()
   rv = db.execute(sql)
   res = rv.fetchone()
   return res[0]

def find_filename(idx):
    sql = "select file from board where rowid = %d" %(int(idx))
    db = get_db()
    rv = db.execute(sql)
    res = rv.fetchone()
    if res is None:
        return res
    else:
        return res[0]

##user information##

@app.route('/join', methods=["GET","POST"])
def join():
    if request.method == "GET":
        return render_template('join.html')
    elif request.method == "POST":
        user_id = request.form.get('user_id')
        user_pw = request.form.get('user_pw')
        hash_pw = hash_password(user_pw)
        nickname = request.form.get('nickname')
        mobile = request.form.get('mobile')
        email = request.form.get('email')
        sql = "insert into users (id, password, nickname, email, mobile) values ('%s','%s','%s','%s','%s')" %(user_id, hash_pw, nickname, email, mobile)
        db = get_db()
        db.execute(sql)
        res = db.commit()
    return redirect(url_for('login'))

@app.route('/checkpassword',methods=['GET','POST'])
def checkpassword():
    if session['user_id'] is not None:
        if request.method == 'GET':
            return render_template('check.html')
        elif request.method == "POST":
            gss = session['user_id']
            sql = "select password from users where id='%s'" %(gss)
            db = get_db()
            rv = db.execute(sql)
            res = rv.fetchone()
            user_pw = request.form.get('checkpassword')
            chpw = hash_password(user_pw)
            if res[0] == chpw:
                return redirect(url_for('modify_userinformation'))
            else:
                return '''
                        <script>
                        alert('Password is no correct!');
                        history.go(-1);
                        </script>
                        '''

@app.route('/moduserinfo', methods=['GET','POST'])
def modify_userinformation():
    if session['user_id'] is not None:
        if request.method == 'GET':
            gss = session['user_id']
            return render_template('moduserinfo.html',gss=gss)
        elif request.method == "POST":
            mobile = request.form.get('mobile')
            email = request.form.get('email')
            nickname = request.form.get('nickname')
            gss = session['user_id']
            if len(mobile) == 0 and len(email) == 0 and len(nickname) == 0:
                return '''<script>
                        alert('input something!');
                        history.go(-1);
                        </script>'''

            elif len(mobile) != 0 and len(email) == 0 and len(nickname) == 0:
                sql = "update users set mobile='%s' where id = '%s'" %(mobile,gss)
                db  = get_db()
                rv = db.execute(sql)
                db.commit()
                return redirect(url_for('secret'))

            elif len(email) != 0 and len(mobile) == 0 and len(nickname) == 0:
                sql = "update users set email='%s' where id='%s'"%(email,gss)
                db = get_db()
                rv = db.execute(sql)
                db.commit()
                return redirect(url_for('secret'))

            elif len(nickname) != 0 and len(mobile) == 0 and len(email) == 0:
                sql = "update users set nickname='%s' where id = '%s'" %(nickname,gss)
                db = get_db()
                rv = db.execute(sql)
                db.commit()
                return redirect(url_for('secret'))

    else:
        return '''<script>
                alert('You can't access this page');
                history.go(-1);
                </script>'''

def get_user(user_id, hash_pw):
    sql = "select * from users where id='%s' and password='%s' limit 2" %(user_id, hash_pw)
    db = get_db()
    rv = db.execute(sql)
    res = rv.fetchall()
    return res

##login##

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == "GET":
        return render_template('login.html')
    elif request.method == "POST":
        user_id = request.form.get('user_id')
        user_pw = request.form.get('user_pw')
        sql = "select id from users where id ='%s'" %(user_id)
        db = get_db()
        rv = db.execute(sql)
        res = rv.fetchone()
        if res is not None:
            if res[0] == user_id:
                hash_pw = hash_password(user_pw)
                chk_buser = get_user(user_id, hash_pw)
                if len(chk_buser) != 0:
                    session['user_id'] = user_id
                    session['hash_pw'] = hash_pw
                    return redirect(url_for('index'))
            else:
                return '''<script>
                        alert('Login Failed!');
                        history.go(-1);
                        </script>'''
        else:
            return '''
                <script>
                alert('Login Failed!');
                history.go(-1);
                </script>
                '''

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('index'))

def hash_password(user_pw):
    res = hashlib.sha224(b"{}".format(user_pw)).hexdigest()
    return res

@app.route('/secret')
def secret():
    if session['user_id'] is not None:
        gss = session['user_id']
        sql = "select email,nickname,mobile from users where id = '%s'" %(gss)
        db = get_db()
        rv = db.execute(sql)
        res = rv.fetchone()
        email = res[0]
        nickname = res[1]
        mobile = res[2]
        return render_template('secret.html',email=email,nickname=nickname,mobile=mobile,gss=gss)
    else:
        return '''
                <script>
                alert('logined user only can access this page!');
                history.go(-1);
                </script>
                '''

@app.route('/withdraw', methods=['GET','POST'])
def withdraw():
    if session['user_id'] is not None:
        gss = session['user_id']
        sql = "delete from users where id = '%s'" %(gss)
        db = get_db()
        rv = db.execute(sql)
        db.commit()
        session.pop('user_id',None)
        return redirect(url_for('index'))
    else:
        return '''<script>alert('User only!'); history.go(-1);</script>'''

##comment##

@app.route('/view/<idx>/comment', methods=['GET','POST'])
def comment(idx):
    if session['user_id'] is not None:
        if request.method == "POST":
            comment = request.form.get('comment')
            date = get_date()
            writer = session['user_id']
            sql = "insert into comment (idx,writer,date,comment) values (%d,'%s','%s','%s')" %(int(idx),writer,date,comment)
            db = get_db()
            rv = db.execute(sql)
            res = db.commit()
            return redirect(url_for("view_post",idx=idx))

@app.route('/modcomment/idx=<idx>/<cdx>', methods=['GET','POST'])
def modify_comment(idx,cdx):
    if session['user_id'] is not None:
        gss = session['user_id']
        res = whosecomment(gss,cdx,idx)
        if res is True:
            if request.method == "GET":
                return render_template('modcomment.html',cdx=int(cdx),idx=int(idx))
            elif request.method == "POST":
                modcom = request.form.get('modcom')
                sql = "update comment set comment = '%s' where idx = %d" %(modcom,int(cdx))
                db = get_db()
                rv = db.execute(sql)
                db.commit()
                return redirect(url_for('view_post',idx=int(idx)))
        else:
            return '<script>alert("Writer only!");history.go(-1);</script>'
    else:
        return '<script>alert("Login First!");history.go(-1);</script>'

@app.route('/delcomment/idx=<idx>/<cdx>', methods=['GET','POST'])
def delete_comment(idx,cdx):
    if session['user_id'] is not None:
        gss = session['user_id']
        res = whosecomment(gss,cdx,idx)
        if res is True:
            if request.method == "GET":
                sql = "delete from comment where writer='%s' and rowid=%d" %(gss,int(cdx))
                db = get_db()
                rv = db.execute(sql)
                db.commit()
                return redirect(url_for('view_post',idx=int(idx)))
        else:
            return '<script>alert("Writer only!");history.go(-1);</script>'
    else:
        return '<script>alert("Login First!");history.go(-1);</script>'

def whosecomment(gss,cdx,idx):
    sql = "select * from comment where rowid=%d and idx= %d and writer = '%s'" %(int(cdx),int(idx),gss)
    db = get_db()
    rv = db.execute(sql)
    res = rv.fetchone()
    if res is None:
        return False
    else:
        return True

##upload file##

def upload_file(idx):
    try:
        os.makedirs('./uploads/'+ str(idx))
        path = './uploads/' + str(idx) +'/'
        f = request.files['_file']
        f.save( path + secure_filename(f.filename))
        fin = path + secure_filename(f.filename)
        sql = "update board set file='%s' where rowid=%d"%(fin,idx)
        db = get_db()
        rv = db.execute(sql)
        db.commit()
        return fin
    except KeyError:
        pass

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0',port=9888)

