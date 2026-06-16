from flask import Flask, request, redirect, session, send_from_directory, render_template_string
import os
import sqlite3
import time
import socket
import secrets
from datetime import timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

# ==============================
# إعدادات تناسب الهاتف
# ==============================
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "tarh_afkar.db")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
SECRET_FILE = os.path.join(BASE_DIR, ".secret_key")

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
MAX_IMAGE_MB = 3

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def load_secret_key():
    if os.path.exists(SECRET_FILE):
        with open(SECRET_FILE, "r", encoding="utf-8") as f:
            key = f.read().strip()
            if key:
                return key

    key = secrets.token_hex(32)
    with open(SECRET_FILE, "w", encoding="utf-8") as f:
        f.write(key)
    return key


app = Flask(__name__)
app.secret_key = load_secret_key()
app.config["MAX_CONTENT_LENGTH"] = MAX_IMAGE_MB * 1024 * 1024
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.permanent_session_lifetime = timedelta(days=30)


def db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def init_db():
    con = db()
    con.executescript("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS articles(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        image TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS likes(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        article_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        UNIQUE(article_id, user_id),
        FOREIGN KEY(article_id) REFERENCES articles(id) ON DELETE CASCADE,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS comments(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        article_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        comment TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY(article_id) REFERENCES articles(id) ON DELETE CASCADE,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """)
    con.commit()
    con.close()


init_db()


STYLE = """
<style>
*{box-sizing:border-box}
body{
    font-family:Arial,Tahoma,sans-serif;
    background:#f4f6f8;
    margin:0;
    direction:rtl;
    color:#222;
}
nav{
    background:white;
    padding:14px;
    box-shadow:0 2px 8px #ddd;
    display:flex;
    gap:12px;
    align-items:center;
    flex-wrap:wrap;
    position:sticky;
    top:0;
    z-index:10;
}
nav a{
    color:#4f46e5;
    text-decoration:none;
    font-weight:bold;
}
.logo{
    font-size:22px;
    color:#4f46e5;
    margin-left:8px;
}
.container{
    max-width:900px;
    margin:22px auto;
    padding:12px;
}
.card{
    background:white;
    padding:18px;
    border-radius:14px;
    margin-bottom:18px;
    box-shadow:0 2px 10px #ddd;
}
input,textarea{
    width:100%;
    padding:12px;
    margin:8px 0;
    border:1px solid #ccc;
    border-radius:10px;
    font-size:16px;
    background:white;
}
textarea{
    resize:vertical;
    line-height:1.8;
}
button{
    background:#4f46e5;
    color:white;
    border:0;
    padding:10px 18px;
    border-radius:10px;
    cursor:pointer;
    font-size:15px;
}
button:hover{
    background:#4338ca;
}
img{
    max-width:100%;
    border-radius:12px;
    margin-top:10px;
}
.small{
    color:#666;
    font-size:14px;
}
.actions{
    display:flex;
    gap:10px;
    align-items:center;
    margin-top:10px;
    flex-wrap:wrap;
}
.comment{
    background:#f1f5f9;
    padding:9px;
    border-radius:8px;
    margin-top:7px;
    line-height:1.7;
}
.article-content{
    white-space:pre-wrap;
    line-height:1.9;
}
.notice{
    background:#eef2ff;
    border:1px solid #c7d2fe;
    color:#312e81;
}
.error{
    background:#fff1f2;
    border:1px solid #fecdd3;
    color:#9f1239;
}
@media(max-width:600px){
    nav{gap:9px;font-size:14px}
    .logo{width:100%;font-size:20px}
    .container{margin:10px auto;padding:10px}
    .card{padding:14px;border-radius:12px}
}
</style>
"""


def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None

    con = db()
    user = con.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    con.close()
    return user


def navbar_html(user):
    return render_template_string("""
    <nav>
        <b class="logo">💡 طرح الأفكار</b>
        <a href="/">الرئيسية</a>
        <a href="/about">عن المنصة</a>

        {% if user %}
            <a href="/publish">نشر مقال</a>
            <a href="/my">مقالاتي</a>
            <a href="/logout">خروج</a>
            <span class="small">مرحباً، {{ user.username }}</span>
        {% else %}
            <a href="/login">دخول</a>
            <a href="/register">حساب جديد</a>
        {% endif %}
    </nav>
    """, user=user)


def render_page(body, status=200, **context):
    user = context.pop("user", current_user())
    html = STYLE + navbar_html(user) + body
    return render_template_string(html, user=user, **context), status


def message_page(title, message, status=200, error=False):
    return render_page("""
    <div class="container">
        <div class="card {{ 'error' if error else 'notice' }}">
            <h2>{{ title }}</h2>
            <p>{{ message }}</p>
            <p><a href="/">الرجوع للرئيسية</a></p>
        </div>
    </div>
    """, status=status, title=title, message=message, error=error)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def save_image(file_storage):
    if not file_storage or not file_storage.filename:
        return None

    original = secure_filename(file_storage.filename)
    if not original:
        return None

    if not allowed_file(original):
        return "__BAD_TYPE__"

    ext = original.rsplit(".", 1)[1].lower()
    new_name = f"{int(time.time())}_{secrets.token_hex(5)}.{ext}"
    file_storage.save(os.path.join(UPLOAD_FOLDER, new_name))
    return new_name


def get_lan_ip():
    sock = None
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        if sock:
            sock.close()


def login_required():
    user = current_user()
    if not user:
        return None, redirect("/login")
    return user, None


@app.errorhandler(413)
def file_too_large(error):
    return message_page(
        "الملف كبير",
        f"حجم الصورة أكبر من {MAX_IMAGE_MB}MB. اختر صورة أصغر وحاول مرة ثانية.",
        status=413,
        error=True
    )


@app.errorhandler(404)
def not_found(error):
    return message_page(
        "الصفحة غير موجودة",
        "الرابط غير صحيح أو الصفحة انحذفت.",
        status=404,
        error=True
    )


@app.route("/")
def home():
    user = current_user()
    q = request.args.get("q", "").strip()

    con = db()

    if q:
        like_pattern = f"%{q}%"
        articles = con.execute("""
            SELECT articles.*, users.username,
            (SELECT COUNT(*) FROM likes WHERE likes.article_id = articles.id) AS likes_count
            FROM articles
            JOIN users ON users.id = articles.user_id
            WHERE users.username LIKE ? OR articles.title LIKE ?
            ORDER BY articles.id DESC
        """, (like_pattern, like_pattern)).fetchall()
    else:
        articles = con.execute("""
            SELECT articles.*, users.username,
            (SELECT COUNT(*) FROM likes WHERE likes.article_id = articles.id) AS likes_count
            FROM articles
            JOIN users ON users.id = articles.user_id
            ORDER BY articles.id DESC
        """).fetchall()

    comments = con.execute("""
        SELECT comments.*, users.username
        FROM comments
        JOIN users ON users.id = comments.user_id
        ORDER BY comments.id ASC
    """).fetchall()

    con.close()

    comments_by_article = {}
    for c in comments:
        comments_by_article.setdefault(c["article_id"], []).append(c)

    return render_page("""
    <div class="container">

        <form method="get" class="card">
            <input name="q" placeholder="ابحث عن اسم ناشر أو عنوان مقال" value="{{ q }}">
            <button type="submit">بحث</button>
            {% if q %}
                <a href="/" style="margin-right:10px">مسح البحث</a>
            {% endif %}
        </form>

        {% for a in articles %}
        <div class="card">
            <h2>{{ a.title }}</h2>
            <p class="small">بواسطة: {{ a.username }} | {{ a.created_at }}</p>
            <p class="article-content">{{ a.content }}</p>

            {% if a.image %}
                <img src="/uploads/{{ a.image }}" alt="صورة المقال">
            {% endif %}

            <div class="actions">
                {% if user %}
                    <form method="post" action="/like/{{ a.id }}">
                        <button type="submit">👍 إعجاب {{ a.likes_count }}</button>
                    </form>
                {% else %}
                    <span>👍 {{ a.likes_count }}</span>
                    <span class="small">سجّل دخولك للتفاعل</span>
                {% endif %}
            </div>

            <h4>التعليقات</h4>

            {% for c in comments_by_article.get(a.id, []) %}
                <div class="comment">
                    <b>{{ c.username }}</b>: {{ c.comment }}
                    <div class="small">{{ c.created_at }}</div>
                </div>
            {% endfor %}

            {% if user %}
            <form method="post" action="/comment/{{ a.id }}">
                <input name="comment" maxlength="300" placeholder="اكتب تعليقك" required>
                <button type="submit">تعليق</button>
            </form>
            {% endif %}
        </div>
        {% else %}
        <div class="card">لا توجد مقالات حالياً.</div>
        {% endfor %}

    </div>
    """, user=user, articles=articles, comments_by_article=comments_by_article, q=q)


@app.route("/about")
def about():
    return render_page("""
    <div class="container">
        <div class="card">
            <h2>عن منصة طرح الأفكار</h2>
            <p>
                منصة طرح الأفكار هي موقع بسيط لنشر المقالات والأفكار ومشاركتها مع الآخرين.
            </p>
            <p>
                يمكنك إنشاء حساب، نشر مقال، رفع صورة، التعليق على مقالات الآخرين، ووضع إعجاب.
            </p>
            <p>
                هذا المشروع معمول بلغة Python باستخدام Flask و SQLite، ومجهّز ليعمل من ملف واحد على الهاتف.
            </p>
        </div>
    </div>
    """)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if len(username) < 3 or len(username) > 30:
            return message_page(
                "خطأ",
                "اسم المستخدم لازم يكون من 3 إلى 30 حرف.",
                status=400,
                error=True
            )

        if len(password) < 4:
            return message_page(
                "خطأ",
                "كلمة المرور لازم تكون 4 أحرف على الأقل.",
                status=400,
                error=True
            )

        con = db()
        try:
            con.execute(
                "INSERT INTO users(username, password) VALUES(?, ?)",
                (username, generate_password_hash(password))
            )
            con.commit()
        except sqlite3.IntegrityError:
            con.close()
            return message_page(
                "اسم موجود",
                "اسم المستخدم موجود من قبل، جرّب اسم ثاني.",
                status=409,
                error=True
            )

        con.close()
        return redirect("/login")

    return render_page("""
    <div class="container">
        <div class="card">
            <h2>إنشاء حساب جديد</h2>
            <form method="post">
                <input name="username" maxlength="30" placeholder="اسم المستخدم" required>
                <input name="password" type="password" placeholder="كلمة المرور" required>
                <button type="submit">تسجيل</button>
            </form>
            <p><a href="/login">عندي حساب</a></p>
        </div>
    </div>
    """)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        con = db()
        user = con.execute(
            "SELECT * FROM users WHERE username=?",
            (username,)
        ).fetchone()
        con.close()

        if user and check_password_hash(user["password"], password):
            session.permanent = True
            session["user_id"] = user["id"]
            return redirect("/")

        return message_page(
            "فشل الدخول",
            "بيانات الدخول غير صحيحة.",
            status=401,
            error=True
        )

    return render_page("""
    <div class="container">
        <div class="card">
            <h2>تسجيل الدخول</h2>
            <form method="post">
                <input name="username" placeholder="اسم المستخدم" required>
                <input name="password" type="password" placeholder="كلمة المرور" required>
                <button type="submit">دخول</button>
            </form>
            <p><a href="/register">إنشاء حساب جديد</a></p>
        </div>
    </div>
    """)


@app.route("/publish", methods=["GET", "POST"])
def publish():
    user, response = login_required()
    if response:
        return response

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()

        if len(title) < 2:
            return message_page(
                "خطأ",
                "اكتب عنواناً واضحاً للمقال.",
                status=400,
                error=True
            )

        if len(content) < 5:
            return message_page(
                "خطأ",
                "محتوى المقال قصير جداً.",
                status=400,
                error=True
            )

        if len(content) > 5000:
            return message_page(
                "خطأ",
                "المقال أكثر من 5000 حرف.",
                status=400,
                error=True
            )

        image_name = save_image(request.files.get("image"))

        if image_name == "__BAD_TYPE__":
            return message_page(
                "نوع صورة غير مدعوم",
                "ارفع صورة بصيغة: png أو jpg أو jpeg أو gif أو webp.",
                status=400,
                error=True
            )

        con = db()
        con.execute("""
            INSERT INTO articles(user_id, title, content, image, created_at)
            VALUES(?, ?, ?, ?, datetime('now', 'localtime'))
        """, (user["id"], title[:120], content, image_name))
        con.commit()
        con.close()

        return redirect("/")

    return render_page("""
    <div class="container">
        <div class="card">
            <h2>نشر مقال جديد</h2>
            <form method="post" enctype="multipart/form-data">
                <input name="title" maxlength="120" placeholder="عنوان المقال" required>
                <textarea name="content" maxlength="5000" rows="10" placeholder="اكتب مقالك هنا حتى 5000 حرف" required></textarea>
                <input type="file" name="image" accept="image/png,image/jpeg,image/gif,image/webp">
                <p class="small">أقصى حجم للصورة: {{ max_mb }}MB</p>
                <button type="submit">نشر</button>
            </form>
        </div>
    </div>
    """, max_mb=MAX_IMAGE_MB)


@app.route("/my")
def my_articles():
    user, response = login_required()
    if response:
        return response

    con = db()
    articles = con.execute(
        "SELECT * FROM articles WHERE user_id=? ORDER BY id DESC",
        (user["id"],)
    ).fetchall()
    con.close()

    return render_page("""
    <div class="container">
        <h2>مقالاتي</h2>

        {% for a in articles %}
        <div class="card">
            <h3>{{ a.title }}</h3>
            <p class="small">{{ a.created_at }}</p>
            <p class="article-content">{{ a.content }}</p>

            {% if a.image %}
                <img src="/uploads/{{ a.image }}" alt="صورة المقال">
            {% endif %}
        </div>
        {% else %}
        <div class="card">ما عندك مقالات حالياً.</div>
        {% endfor %}
    </div>
    """, user=user, articles=articles)


@app.route("/like/<int:article_id>", methods=["POST"])
def like(article_id):
    user, response = login_required()
    if response:
        return response

    con = db()

    article = con.execute(
        "SELECT id FROM articles WHERE id=?",
        (article_id,)
    ).fetchone()

    if not article:
        con.close()
        return message_page(
            "خطأ",
            "المقال غير موجود.",
            status=404,
            error=True
        )

    try:
        con.execute(
            "INSERT INTO likes(article_id, user_id) VALUES(?, ?)",
            (article_id, user["id"])
        )
    except sqlite3.IntegrityError:
        con.execute(
            "DELETE FROM likes WHERE article_id=? AND user_id=?",
            (article_id, user["id"])
        )

    con.commit()
    con.close()

    return redirect(request.referrer or "/")


@app.route("/comment/<int:article_id>", methods=["POST"])
def comment(article_id):
    user, response = login_required()
    if response:
        return response

    text = request.form.get("comment", "").strip()[:300]

    if not text:
        return redirect(request.referrer or "/")

    con = db()

    article = con.execute(
        "SELECT id FROM articles WHERE id=?",
        (article_id,)
    ).fetchone()

    if not article:
        con.close()
        return message_page(
            "خطأ",
            "المقال غير موجود.",
            status=404,
            error=True
        )

    con.execute("""
        INSERT INTO comments(article_id, user_id, comment, created_at)
        VALUES(?, ?, ?, datetime('now', 'localtime'))
    """, (article_id, user["id"], text))

    con.commit()
    con.close()

    return redirect(request.referrer or "/")


@app.route("/uploads/<path:filename>")
def uploads(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


if __name__ == "__main__":
    port = 5000
    lan_ip = get_lan_ip()

    print("\n==============================")
    print("منصة طرح الأفكار اشتغلت ✅")
    print(f"افتح من نفس الهاتف: http://127.0.0.1:{port}")
    print(f"افتح من جهاز ثاني على نفس الواي فاي: http://{lan_ip}:{port}")
    print("لإيقاف السيرفر اضغط CTRL + C")
    print("==============================\n")

    app.run(host="0.0.0.0", port=port, debug=False)