from flask import Flask, request, redirect, session, send_from_directory, render_template_string, jsonify
import os
import sqlite3
import time
import socket
import secrets
import re
from datetime import timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

DATA_DIR = os.environ.get(
    "DATA_DIR",
    os.path.join(os.path.expanduser("~"), "tarh_afkar_data")
)

DB_PATH = os.path.join(DATA_DIR, "tarh_afkar.db")
UPLOAD_FOLDER = os.path.join(DATA_DIR, "uploads")
SECRET_FILE = os.path.join(DATA_DIR, ".secret_key")
BACKUP_FOLDER = os.path.join(DATA_DIR, "backups")

IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
VIDEO_EXTENSIONS = {"mp4", "webm", "mov", "avi", "mkv"}
MAX_UPLOAD_MB = 100
ONLINE_SECONDS = 90
MAX_BACKUPS = 25
HASHTAG_RE = re.compile(r"(?<!\w)#([\w\u0600-\u06FF]{2,40})")

CATEGORIES = ["عام", "تاريخي", "ديني", "اجتماعي", "تطوير الذات", "ترفيهي", "رياضة", "علمي", "تقني"]

LOGO_DATA_URL = "data:image/webp;base64,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"

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(BACKUP_FOLDER, exist_ok=True)


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
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_MB * 1024 * 1024
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.permanent_session_lifetime = timedelta(days=30)


def db():
    con = sqlite3.connect(DB_PATH, timeout=30.0)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.execute("PRAGMA journal_mode = WAL")
    con.execute("PRAGMA synchronous = FULL")
    con.execute("PRAGMA busy_timeout = 30000")
    return con


def column_exists(con, table, column):
    rows = con.execute(f"PRAGMA table_info({table})").fetchall()
    return any(r["name"] == column for r in rows)


def add_column_if_missing(con, table, column, definition):
    if not column_exists(con, table, column):
        con.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


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
        video TEXT,
        category TEXT DEFAULT 'عام',
        views INTEGER DEFAULT 0,
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

    CREATE TABLE IF NOT EXISTS messages(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender_id INTEGER NOT NULL,
        receiver_id INTEGER NOT NULL,
        body TEXT NOT NULL,
        is_read INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL,
        FOREIGN KEY(sender_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY(receiver_id) REFERENCES users(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS hashtags(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tag TEXT NOT NULL UNIQUE,
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS article_hashtags(
        article_id INTEGER NOT NULL,
        hashtag_id INTEGER NOT NULL,
        PRIMARY KEY(article_id, hashtag_id),
        FOREIGN KEY(article_id) REFERENCES articles(id) ON DELETE CASCADE,
        FOREIGN KEY(hashtag_id) REFERENCES hashtags(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS saved_articles(
        user_id INTEGER NOT NULL,
        article_id INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        PRIMARY KEY(user_id, article_id),
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY(article_id) REFERENCES articles(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS follows(
        follower_id INTEGER NOT NULL,
        following_id INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        PRIMARY KEY(follower_id, following_id),
        FOREIGN KEY(follower_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY(following_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """)

    add_column_if_missing(con, "users", "bio", "TEXT DEFAULT ''")
    add_column_if_missing(con, "users", "avatar", "TEXT")
    add_column_if_missing(con, "users", "last_seen", "INTEGER DEFAULT 0")
    add_column_if_missing(con, "users", "created_at", "TEXT DEFAULT ''")
    add_column_if_missing(con, "users", "full_name", "TEXT DEFAULT ''")
    add_column_if_missing(con, "articles", "category", "TEXT DEFAULT 'عام'")
    add_column_if_missing(con, "articles", "views", "INTEGER DEFAULT 0")
    add_column_if_missing(con, "articles", "video", "TEXT")

    con.execute("CREATE INDEX IF NOT EXISTS idx_articles_user ON articles(user_id)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_articles_category ON articles(category)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_messages_sender ON messages(sender_id)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_messages_receiver ON messages(receiver_id)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_saved_user ON saved_articles(user_id)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_follows_follower ON follows(follower_id)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_follows_following ON follows(following_id)")

    con.commit()
    con.close()


init_db()

STYLE = """
<style>
:root{
    --navy:#081d35;
    --navy2:#0d2b4c;
    --gold:#f7b91e;
    --gold2:#ffd772;
    --white:#ffffff;
    --soft:#f5f7fb;
    --muted:#64748b;
    --line:#e6edf5;
    --red:#e11d48;
    --green:#16a34a;
    --shadow:0 18px 45px rgba(8,29,53,.10);
    --shadow2:0 10px 30px rgba(8,29,53,.08);
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{
    font-family:Arial,Tahoma,sans-serif;
    background:
        radial-gradient(circle at top right,rgba(247,185,30,.16),transparent 32%),
        radial-gradient(circle at bottom left,rgba(8,29,53,.12),transparent 35%),
        linear-gradient(180deg,#f8fafc 0%,#eef3f9 100%);
    margin:0;
    direction:rtl;
    color:#132033;
    min-height:100vh;
}
a{color:var(--navy2);text-decoration:none;font-weight:800}
img,video{max-width:100%;border-radius:22px;margin-top:12px}
video{width:100%;background:#000}
nav{
    background:rgba(255,255,255,.82);
    backdrop-filter:blur(18px);
    -webkit-backdrop-filter:blur(18px);
    border-bottom:1px solid rgba(230,237,245,.9);
    box-shadow:0 10px 35px rgba(8,29,53,.08);
    display:flex;
    gap:10px;
    align-items:center;
    flex-wrap:wrap;
    position:sticky;
    top:0;
    z-index:50;
    padding:12px 18px;
}
.brand{
    display:flex;
    align-items:center;
    gap:10px;
    margin-left:8px;
}
.logo-img{
    width:58px;
    height:58px;
    border-radius:50%;
    object-fit:cover;
    box-shadow:0 10px 24px rgba(8,29,53,.22);
    border:3px solid rgba(247,185,30,.75);
}
.brand-title{
    display:flex;
    flex-direction:column;
    line-height:1.1;
}
.brand-title b{
    color:var(--navy);
    font-size:18px;
}
.brand-title span{
    color:var(--muted);
    font-size:12px;
    font-weight:700;
}
.nav-link{
    color:var(--navy);
    background:rgba(245,247,251,.85);
    border:1px solid rgba(230,237,245,.9);
    padding:10px 13px;
    border-radius:999px;
    font-size:14px;
    transition:.2s;
}
.nav-link:hover{
    background:var(--navy);
    color:var(--gold2);
    transform:translateY(-1px);
}
.container{
    width:min(1080px,100%);
    margin:0 auto;
    padding:18px;
}
.hero{
    background:
        linear-gradient(135deg,rgba(8,29,53,.96),rgba(13,43,76,.92)),
        radial-gradient(circle at 20% 0%,rgba(247,185,30,.26),transparent 28%);
    border:1px solid rgba(247,185,30,.28);
    box-shadow:var(--shadow);
    border-radius:30px;
    padding:24px;
    margin:18px 0;
    color:white;
    overflow:hidden;
    position:relative;
}
.hero:before{
    content:"";
    position:absolute;
    inset:auto -80px -100px auto;
    width:260px;
    height:260px;
    border-radius:50%;
    background:rgba(247,185,30,.18);
    filter:blur(4px);
}
.hero-content{
    display:flex;
    gap:18px;
    align-items:center;
    position:relative;
    z-index:1;
}
.hero-logo{
    width:92px;
    height:92px;
    border-radius:50%;
    border:3px solid var(--gold);
    box-shadow:0 18px 35px rgba(0,0,0,.25);
    object-fit:cover;
    flex:0 0 auto;
}
.hero h1{
    margin:0 0 8px;
    font-size:30px;
    letter-spacing:-.5px;
}
.hero p{
    margin:0;
    color:#d8e4f2;
    line-height:1.8;
}
.card{
    background:rgba(255,255,255,.92);
    backdrop-filter:blur(10px);
    border:1px solid rgba(230,237,245,.95);
    padding:20px;
    border-radius:26px;
    margin-bottom:16px;
    box-shadow:var(--shadow2);
}
.article-card{
    padding:0;
    overflow:hidden;
}
.article-inner{
    padding:20px;
}
input,textarea,select{
    width:100%;
    padding:14px 15px;
    margin:8px 0;
    border:1px solid #d9e2ee;
    border-radius:17px;
    font-size:16px;
    background:#fff;
    color:#132033;
    outline:none;
    transition:.2s;
}
input:focus,textarea:focus,select:focus{
    border-color:var(--gold);
    box-shadow:0 0 0 4px rgba(247,185,30,.18);
}
textarea{resize:vertical;line-height:1.8}
button,.btn{
    background:linear-gradient(135deg,var(--navy),var(--navy2));
    color:white;
    border:0;
    padding:11px 17px;
    border-radius:999px;
    cursor:pointer;
    font-size:15px;
    font-weight:800;
    display:inline-flex;
    align-items:center;
    justify-content:center;
    gap:6px;
    transition:.2s;
    box-shadow:0 8px 18px rgba(8,29,53,.12);
}
button:hover,.btn:hover{
    transform:translateY(-1px);
    color:white;
    box-shadow:0 14px 24px rgba(8,29,53,.18);
}
.btn-light{
    background:#fff8e6;
    color:#6b4b00;
    border:1px solid rgba(247,185,30,.35);
}
.btn-light:hover{
    background:var(--gold);
    color:var(--navy);
}
.btn-danger{
    background:linear-gradient(135deg,#e11d48,#be123c);
}
.small{color:var(--muted);font-size:14px}
.actions{
    display:flex;
    gap:9px;
    align-items:center;
    margin-top:12px;
    flex-wrap:wrap;
}
.comment{
    background:#f8fafc;
    border:1px solid var(--line);
    padding:12px;
    border-radius:18px;
    margin-top:10px;
    line-height:1.8;
}
.article-content{
    white-space:pre-wrap;
    line-height:2;
    color:#26384f;
    font-size:16px;
}
.notice{
    background:#fff8e6;
    border:1px solid rgba(247,185,30,.45);
    color:#4d3700;
}
.error{
    background:#fff1f2;
    border:1px solid #fecdd3;
    color:#9f1239;
}
.profile-row{
    display:flex;
    gap:14px;
    align-items:center;
}
.avatar{
    width:58px;
    height:58px;
    border-radius:50%;
    object-fit:cover;
    background:#e2e8f0;
    border:3px solid #fff;
    box-shadow:0 8px 18px rgba(8,29,53,.12);
}
.avatar-big{
    width:112px;
    height:112px;
    border-radius:50%;
    object-fit:cover;
    background:#e2e8f0;
    border:4px solid #fff;
    box-shadow:0 12px 28px rgba(8,29,53,.16);
}
.online{color:var(--green);font-weight:900}
.offline{color:var(--muted)}
.message{
    padding:12px 14px;
    border-radius:18px;
    margin:8px 0;
    max-width:82%;
    line-height:1.7;
}
.mine{
    background:linear-gradient(135deg,var(--navy),var(--navy2));
    color:white;
    margin-right:auto;
}
.theirs{
    background:#f1f5f9;
    border:1px solid var(--line);
    margin-left:auto;
}
.chat-box{
    max-height:430px;
    overflow:auto;
    padding:12px;
    background:#fbfdff;
    border-radius:22px;
    border:1px solid var(--line);
}
.badge{
    background:var(--red);
    color:white;
    border-radius:999px;
    padding:2px 7px;
    font-size:12px;
}
.category-badge,.tag-badge{
    background:linear-gradient(135deg,var(--gold),var(--gold2));
    color:var(--navy);
    border-radius:999px;
    padding:4px 10px;
    font-size:13px;
    font-weight:900;
    display:inline-block;
    margin:3px;
}
.tag-badge{
    background:#edf4ff;
    color:var(--navy2);
    border:1px solid #dbeafe;
}
.searchbar{
    display:flex;
    gap:10px;
    align-items:center;
}
.searchbar input{margin:0}
.cat-scroll{
    display:flex;
    gap:10px;
    overflow-x:auto;
    white-space:nowrap;
    padding-bottom:4px;
}
.cat-scroll::-webkit-scrollbar{height:6px}
.cat-scroll::-webkit-scrollbar-thumb{background:#d7e0ee;border-radius:999px}
.post-media{
    width:100%;
    display:block;
    border-radius:0;
    margin:0;
    max-height:680px;
    object-fit:cover;
    background:#eef2f7;
}
.article-header{
    display:flex;
    gap:14px;
    align-items:center;
    margin-bottom:10px;
}
.article-title{
    margin:0;
    font-size:24px;
    color:var(--navy);
}
.page-title{
    margin:8px 0 16px;
    color:var(--navy);
}
.form-title{
    margin-top:0;
    color:var(--navy);
}
.empty{
    text-align:center;
    padding:28px;
    color:var(--muted);
}
@media(max-width:760px){
    .container{padding:10px}
    nav{gap:8px;padding:10px}
    .brand{width:100%;justify-content:center;margin-left:0}
    .brand-title{text-align:right}
    .nav-link{font-size:13px;padding:9px 11px}
    .card{padding:15px;border-radius:22px}
    .article-inner{padding:15px}
    .message{max-width:92%}
    .searchbar{display:block}
    .searchbar button{width:100%;margin-top:8px}
    .hero{border-radius:24px;padding:18px}
    .hero-content{align-items:flex-start}
    .hero-logo{width:74px;height:74px}
    .hero h1{font-size:23px}
    .profile-row{align-items:flex-start}
    .article-title{font-size:20px}
}
</style>
"""


def safe_text(text, limit):
    return (text or "").strip()[:limit]


def normalize_username(username):
    username = (username or "").strip().lower()
    username = re.sub(r"[^a-z0-9_\u0600-\u06FF]", "", username)
    return username[:30]


def extract_hashtags(*texts):
    found = []
    for text in texts:
        for tag in HASHTAG_RE.findall(text or ""):
            tag = tag.strip().lower().replace("ـ", "")[:40]
            if tag and tag not in found:
                found.append(tag)
    return found[:12]


def sync_article_hashtags(con, article_id, *texts):
    con.execute("DELETE FROM article_hashtags WHERE article_id=?", (article_id,))
    for tag in extract_hashtags(*texts):
        con.execute(
            "INSERT OR IGNORE INTO hashtags(tag, created_at) VALUES(?, datetime('now','localtime'))",
            (tag,)
        )
        hashtag_id = con.execute("SELECT id FROM hashtags WHERE tag=?", (tag,)).fetchone()["id"]
        con.execute(
            "INSERT OR IGNORE INTO article_hashtags(article_id, hashtag_id) VALUES(?, ?)",
            (article_id, hashtag_id)
        )


def get_article_tags(con, article_id):
    return con.execute("""
        SELECT hashtags.tag FROM hashtags
        JOIN article_hashtags ON article_hashtags.hashtag_id=hashtags.id
        WHERE article_hashtags.article_id=?
        ORDER BY hashtags.tag ASC
    """, (article_id,)).fetchall()


def make_backup(reason="auto"):
    if not os.path.exists(DB_PATH):
        return None

    stamp = time.strftime("%Y%m%d_%H%M%S")
    target_name = f"tarh_afkar_{reason}_{stamp}.db"
    target = os.path.join(BACKUP_FOLDER, target_name)

    try:
        source_con = db()
        backup_con = sqlite3.connect(target)
        source_con.backup(backup_con)
        backup_con.close()
        source_con.close()

        backups = sorted(
            [os.path.join(BACKUP_FOLDER, x) for x in os.listdir(BACKUP_FOLDER) if x.endswith(".db")],
            key=os.path.getmtime,
            reverse=True
        )

        for old in backups[MAX_BACKUPS:]:
            os.remove(old)

        return target_name
    except Exception as e:
        print("Backup Error:", e)
        return None


def is_online(user_row):
    return bool(user_row) and int(time.time()) - int(user_row["last_seen"] or 0) <= ONLINE_SECONDS


def online_label(user_row):
    return "أونلاين" if is_online(user_row) else "غير متصل"


def has_extension(filename, extensions):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in extensions


def save_file(file_storage, extensions):
    if not file_storage or not file_storage.filename:
        return None

    original = secure_filename(file_storage.filename)
    if not original or not has_extension(original, extensions):
        return "__BAD_TYPE__"

    ext = original.rsplit(".", 1)[1].lower()
    new_name = f"{int(time.time())}_{secrets.token_hex(12)}.{ext}"
    file_storage.save(os.path.join(UPLOAD_FOLDER, new_name))
    return new_name


def save_image(file_storage):
    return save_file(file_storage, IMAGE_EXTENSIONS)


def save_video(file_storage):
    return save_file(file_storage, VIDEO_EXTENSIONS)


def delete_upload(filename):
    if not filename:
        return

    filename = os.path.basename(filename)
    path = os.path.join(UPLOAD_FOLDER, filename)

    if os.path.exists(path):
        os.remove(path)


def current_user(update_seen=True):
    user_id = session.get("user_id")
    if not user_id:
        return None

    con = db()

    if update_seen:
        con.execute("UPDATE users SET last_seen=? WHERE id=?", (int(time.time()), user_id))
        con.commit()

    user = con.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    con.close()
    return user


def unread_count(user_id):
    con = db()
    count = con.execute(
        "SELECT COUNT(*) AS c FROM messages WHERE receiver_id=? AND is_read=0",
        (user_id,)
    ).fetchone()["c"]
    con.close()
    return count


def generate_csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(16)
    return session["csrf_token"]


def navbar_html():
    return """
    <nav>
        <a class="brand" href="/">
            <img class="logo-img" src="{{ logo_url }}" alt="طرح أفكار">
            <span class="brand-title">
                <b>طرح أفكار</b>
                <span>منصة الأفكار والمقالات</span>
            </span>
        </a>

        <a class="nav-link" href="/">الرئيسية</a>
        <a class="nav-link" href="/users">الأعضاء</a>
        <a class="nav-link" href="/about">عن المنصة</a>

        {% if user %}
            <a class="nav-link" href="/publish">نشر مقال</a>
            <a class="nav-link" href="/my">مقالاتي</a>
            <a class="nav-link" href="/messages">المحادثات {% if unread %}<span class="badge">{{ unread }}</span>{% endif %}</a>
            <a class="nav-link" href="/saved">المحفوظات</a>
            <a class="nav-link" href="/profile">بروفايلي</a>
            <a class="nav-link" href="/backup_now">نسخة احتياطية</a>
            <a class="nav-link" href="/logout">خروج</a>
        {% else %}
            <a class="nav-link" href="/login">دخول</a>
            <a class="nav-link" href="/register">حساب جديد</a>
        {% endif %}
    </nav>
    """


def render_page(body, status=200, **context):
    user = context.pop("user", current_user())
    unread = unread_count(user["id"]) if user else 0
    html = STYLE + navbar_html() + body

    return render_template_string(
        html,
        user=user,
        unread=unread,
        csrf_token=generate_csrf_token(),
        is_online=is_online,
        online_label=online_label,
        CATEGORIES=CATEGORIES,
        logo_url=LOGO_DATA_URL,
        **context
    ), status


def message_page(title, message, status=200, error=False):
    return render_page("""
    <div class="container">
        <div class="card {{ 'error' if error else 'notice' }}">
            <h2>{{ title }}</h2>
            <p>{{ message }}</p>
            <a class="btn btn-light" href="/">الرجوع للرئيسية</a>
        </div>
    </div>
    """, status=status, title=title, message=message, error=error)


def login_required():
    user = current_user()
    if not user:
        return None, redirect("/login")
    return user, None


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


@app.before_request
def csrf_protect():
    if request.method == "POST":
        token = request.form.get("csrf_token")
        if not token or token != session.get("csrf_token"):
            return message_page("خطأ أمني", "الطلب غير صالح. حدّث الصفحة وجرب مرة ثانية.", 403, True)


@app.after_request
def add_security_headers(response):
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


@app.errorhandler(413)
def file_too_large(error):
    return message_page("الملف كبير", f"أقصى حجم للرفع {MAX_UPLOAD_MB}MB.", 413, True)


@app.errorhandler(404)
def not_found(error):
    return message_page("الصفحة غير موجودة", "الرابط غير صحيح أو الصفحة انحذفت.", 404, True)


@app.route("/")
def home():
    user = current_user()
    q = request.args.get("q", "").strip()
    cat = request.args.get("cat", "").strip()

    con = db()
    params = []
    where = []

    if cat in CATEGORIES:
        where.append("articles.category=?")
        params.append(cat)

    if q:
        p = f"%{q}%"
        where.append("(users.username LIKE ? OR users.full_name LIKE ? OR articles.title LIKE ? OR articles.content LIKE ?)")
        params.extend([p, p, p, p])

    where_sql = "WHERE " + " AND ".join(where) if where else ""

    articles = con.execute(f"""
        SELECT articles.*, users.username, users.full_name, users.avatar, users.last_seen,
        (SELECT COUNT(*) FROM likes WHERE likes.article_id=articles.id) AS likes_count,
        (SELECT COUNT(*) FROM comments WHERE comments.article_id=articles.id) AS comments_count
        FROM articles
        JOIN users ON users.id=articles.user_id
        {where_sql}
        ORDER BY articles.id DESC
        LIMIT 50
    """, params).fetchall()

    con.close()

    return render_page("""
    <div class="container">
        <section class="hero">
            <div class="hero-content">
                <img class="hero-logo" src="{{ logo_url }}" alt="طرح أفكار">
                <div>
                    <h1>منصة طرح أفكار</h1>
                    <p>اكتب أفكارك، شارك مقالاتك، تابع الأعضاء، واحفظ أفضل المنشورات في مساحة عربية عصرية.</p>
                </div>
            </div>
        </section>

        <div class="card">
            <div class="cat-scroll">
                <a class="btn {% if not cat %}mine{% else %}btn-light{% endif %}" href="/">الكل</a>
                {% for c in CATEGORIES %}
                    <a class="btn {% if cat == c %}mine{% else %}btn-light{% endif %}" href="/?cat={{ c }}">{{ c }}</a>
                {% endfor %}
            </div>
        </div>

        <form method="get" class="card searchbar">
            {% if cat %}<input type="hidden" name="cat" value="{{ cat }}">{% endif %}
            <input name="q" placeholder="ابحث عن مقال أو ناشر" value="{{ q }}">
            <button>بحث</button>
        </form>

        {% for a in articles %}
        <div class="card article-card">
            {% if a.image %}<img class="post-media" src="/uploads/{{ a.image }}">{% endif %}
            {% if a.video %}
                <video class="post-media" controls preload="metadata">
                    <source src="/uploads/{{ a.video }}">
                    متصفحك لا يدعم تشغيل الفيديو.
                </video>
            {% endif %}

            <div class="article-inner">
                <div class="article-header">
                    {% if a.avatar %}<img class="avatar" src="/uploads/{{ a.avatar }}">{% else %}<div class="avatar"></div>{% endif %}
                    <div>
                        <h2 class="article-title"><a href="/article/{{ a.id }}">{{ a.title }}</a> <span class="category-badge">{{ a.category }}</span></h2>
                        <p class="small">
                            بواسطة: <a href="/user/{{ a.user_id }}">{{ a.full_name or a.username }}</a>
                            | {{ a.created_at }}
                            | 👁️ {{ a.views }}
                            | <span class="{{ 'online' if is_online(a) else 'offline' }}">{{ online_label(a) }}</span>
                        </p>
                    </div>
                </div>

                <p class="article-content">{{ a.content[:700] }}{% if a.content|length > 700 %}...{% endif %}</p>

                <div class="actions">
                    <a class="btn btn-light" href="/article/{{ a.id }}">قراءة كاملة</a>

                    {% if user %}
                    <form method="post" action="/like/{{ a.id }}">
                        <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
                        <button>👍 إعجاب {{ a.likes_count }}</button>
                    </form>
                    {% else %}
                        <span>👍 {{ a.likes_count }}</span>
                    {% endif %}

                    <span class="small">💬 {{ a.comments_count }}</span>

                    {% if user %}
                    <form method="post" action="/save_article/{{ a.id }}">
                        <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
                        <button class="btn-light">🔖 حفظ</button>
                    </form>
                    {% endif %}

                    {% if user and user.id != a.user_id %}
                        <a class="btn btn-light" href="/chat/{{ a.user_id }}">مراسلة</a>
                    {% endif %}

                    {% if user and user.id == a.user_id %}
                        <form method="post" action="/delete_article/{{ a.id }}" onsubmit="return confirm('حذف المقال نهائياً؟')">
                            <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
                            <button class="btn-danger">حذف</button>
                        </form>
                    {% endif %}
                </div>
            </div>
        </div>
        {% else %}
        <div class="card empty">لا توجد مقالات حالياً.</div>
        {% endfor %}
    </div>
    """, user=user, articles=articles, q=q, cat=cat)


@app.route("/article/<int:article_id>")
def article_details(article_id):
    me = current_user()

    con = db()
    con.execute("UPDATE articles SET views = COALESCE(views,0) + 1 WHERE id=?", (article_id,))
    con.commit()

    article = con.execute("""
        SELECT articles.*, users.username, users.full_name, users.avatar, users.last_seen
        FROM articles
        JOIN users ON users.id=articles.user_id
        WHERE articles.id=?
    """, (article_id,)).fetchone()

    if not article:
        con.close()
        return message_page("غير موجود", "المقال غير موجود.", 404, True)

    comments = con.execute("""
        SELECT comments.*, users.username
        FROM comments
        JOIN users ON users.id=comments.user_id
        WHERE comments.article_id=?
        ORDER BY comments.id ASC
    """, (article_id,)).fetchall()

    likes_count = con.execute("SELECT COUNT(*) AS c FROM likes WHERE article_id=?", (article_id,)).fetchone()["c"]
    tags = get_article_tags(con, article_id)
    con.close()

    share_url = request.host_url.rstrip("/") + f"/article/{article_id}"

    return render_page("""
    <div class="container">
        <div class="card article-card">
            {% if article.image %}<img class="post-media" src="/uploads/{{ article.image }}">{% endif %}
            {% if article.video %}
                <video class="post-media" controls preload="metadata">
                    <source src="/uploads/{{ article.video }}">
                    متصفحك لا يدعم تشغيل الفيديو.
                </video>
            {% endif %}

            <div class="article-inner">
                <div class="article-header">
                    {% if article.avatar %}<img class="avatar" src="/uploads/{{ article.avatar }}">{% else %}<div class="avatar"></div>{% endif %}
                    <div>
                        <h2 class="article-title">{{ article.title }} <span class="category-badge">{{ article.category }}</span></h2>
                        <p class="small">
                            بواسطة: <a href="/user/{{ article.user_id }}">{{ article.full_name or article.username }}</a>
                            | {{ article.created_at }}
                            | 👁️ {{ article.views }}
                        </p>
                    </div>
                </div>

                <p class="article-content">{{ article.content }}</p>

                {% if tags %}
                <div style="margin-top:10px">
                    {% for t in tags %}<a class="tag-badge" href="/hashtag/{{ t.tag }}">#{{ t.tag }}</a>{% endfor %}
                </div>
                {% endif %}

                <div class="actions">
                    <input value="{{ share_url }}" readonly onclick="this.select()">

                    {% if user %}
                    <form method="post" action="/like/{{ article.id }}">
                        <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
                        <button>👍 إعجاب {{ likes_count }}</button>
                    </form>

                    <form method="post" action="/save_article/{{ article.id }}">
                        <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
                        <button class="btn-light">🔖 حفظ</button>
                    </form>
                    {% endif %}
                </div>
            </div>
        </div>

        <div class="card">
            <h3 class="form-title">التعليقات</h3>

            {% for c in comments %}
            <div class="comment">
                <b>{{ c.username }}</b>: {{ c.comment }}
                <div class="small">{{ c.created_at }}</div>

                {% if user and (user.id == c.user_id or user.id == article.user_id) %}
                <form method="post" action="/delete_comment/{{ c.id }}" style="margin-top:6px">
                    <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
                    <button class="btn-danger">حذف التعليق</button>
                </form>
                {% endif %}
            </div>
            {% else %}
            <p class="small">لا توجد تعليقات.</p>
            {% endfor %}

            {% if user %}
            <form method="post" action="/comment/{{ article.id }}">
                <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
                <input name="comment" maxlength="300" placeholder="اكتب تعليقك" required>
                <button>تعليق</button>
            </form>
            {% endif %}
        </div>
    </div>
    """, user=me, article=article, comments=comments, likes_count=likes_count, share_url=share_url, tags=tags)


@app.route("/publish", methods=["GET", "POST"])
def publish():
    user, response = login_required()
    if response:
        return response

    if request.method == "POST":
        title = safe_text(request.form.get("title"), 120)
        content = safe_text(request.form.get("content"), 5000)
        extra_hashtags = safe_text(request.form.get("hashtags"), 300)
        category = request.form.get("category", "عام")

        if category not in CATEGORIES:
            category = "عام"

        if len(title) < 2 or len(content) < 5:
            return message_page("خطأ", "اكتب عنوان ومحتوى واضح.", 400, True)

        image_name = save_image(request.files.get("image"))
        if image_name == "__BAD_TYPE__":
            return message_page("نوع صورة غير مدعوم", "ارفع صورة png أو jpg أو jpeg أو gif أو webp.", 400, True)

        video_name = save_video(request.files.get("video"))
        if video_name == "__BAD_TYPE__":
            return message_page("نوع فيديو غير مدعوم", "ارفع فيديو بصيغة mp4 أو webm أو mov أو avi أو mkv.", 400, True)

        make_backup("before_publish")

        con = db()
        cur = con.execute("""
            INSERT INTO articles(user_id,title,content,category,image,video,created_at,views)
            VALUES(?,?,?,?,?,?,datetime('now','localtime'),0)
        """, (user["id"], title, content, category, image_name, video_name))

        article_id = cur.lastrowid
        sync_article_hashtags(con, article_id, title, content, extra_hashtags)
        con.commit()
        con.close()

        return redirect("/")

    return render_page("""
    <div class="container">
        <div class="card">
            <h2 class="form-title">نشر مقال جديد</h2>

            <form method="post" enctype="multipart/form-data">
                <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
                <input name="title" maxlength="120" placeholder="عنوان المقال" required>

                <select name="category" required>
                    {% for c in CATEGORIES %}
                        <option value="{{ c }}">{{ c }}</option>
                    {% endfor %}
                </select>

                <textarea name="content" maxlength="5000" rows="10" placeholder="اكتب مقالك هنا حتى 5000 حرف" required></textarea>
                <input name="hashtags" maxlength="300" placeholder="هاشتاقات اختيارية مثل: #تاريخ #أفكار #تقنية">

                <label class="small">صورة اختيارية</label>
                <input type="file" name="image" accept="image/png,image/jpeg,image/gif,image/webp">

                <label class="small">فيديو اختياري</label>
                <input type="file" name="video" accept="video/mp4,video/webm,video/quicktime,video/x-msvideo,video/x-matroska">

                <p class="small">أقصى حجم للرفع: {{ max_mb }}MB</p>
                <button>نشر</button>
            </form>
        </div>
    </div>
    """, max_mb=MAX_UPLOAD_MB)


@app.route("/my")
def my_articles():
    user, response = login_required()
    if response:
        return response

    con = db()
    articles = con.execute("SELECT * FROM articles WHERE user_id=? ORDER BY id DESC", (user["id"],)).fetchall()
    con.close()

    return render_page("""
    <div class="container">
        <h2 class="page-title">مقالاتي</h2>

        {% for a in articles %}
        <div class="card article-card">
            {% if a.image %}<img class="post-media" src="/uploads/{{ a.image }}">{% endif %}
            {% if a.video %}<video class="post-media" controls preload="metadata"><source src="/uploads/{{ a.video }}"></video>{% endif %}

            <div class="article-inner">
                <h3><a href="/article/{{ a.id }}">{{ a.title }}</a> <span class="category-badge">{{ a.category }}</span></h3>
                <p class="small">{{ a.created_at }} | 👁️ {{ a.views }}</p>
                <p class="article-content">{{ a.content[:500] }}{% if a.content|length > 500 %}...{% endif %}</p>

                <div class="actions">
                    <a class="btn btn-light" href="/article/{{ a.id }}">فتح</a>
                    <form method="post" action="/delete_article/{{ a.id }}" onsubmit="return confirm('حذف المقال نهائياً؟')">
                        <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
                        <button class="btn-danger">حذف</button>
                    </form>
                </div>
            </div>
        </div>
        {% else %}
        <div class="card empty">ما عندك مقالات حالياً.</div>
        {% endfor %}
    </div>
    """, user=user, articles=articles)


@app.route("/user/<int:user_id>")
def public_profile(user_id):
    me = current_user()

    con = db()
    profile_user = con.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()

    if not profile_user:
        con.close()
        return message_page("غير موجود", "هذا الحساب غير موجود.", 404, True)

    articles = con.execute("SELECT * FROM articles WHERE user_id=? ORDER BY id DESC", (user_id,)).fetchall()
    followers_count = con.execute("SELECT COUNT(*) AS c FROM follows WHERE following_id=?", (user_id,)).fetchone()["c"]
    following_count = con.execute("SELECT COUNT(*) AS c FROM follows WHERE follower_id=?", (user_id,)).fetchone()["c"]

    is_following = False
    if me:
        is_following = con.execute(
            "SELECT 1 FROM follows WHERE follower_id=? AND following_id=?",
            (me["id"], user_id)
        ).fetchone() is not None

    con.close()

    return render_page("""
    <div class="container">
        <div class="card profile-row">
            {% if profile_user.avatar %}<img class="avatar-big" src="/uploads/{{ profile_user.avatar }}">{% else %}<div class="avatar-big"></div>{% endif %}

            <div>
                <h2 class="form-title">{{ profile_user.full_name or profile_user.username }}</h2>
                <p class="small">@{{ profile_user.username }} | <span class="{{ 'online' if is_online(profile_user) else 'offline' }}">{{ online_label(profile_user) }}</span></p>
                <p>{{ profile_user.bio or 'لا توجد نبذة.' }}</p>
                <p class="small">المتابعون: {{ followers_count }} | يتابع: {{ following_count }}</p>

                {% if me and me.id != profile_user.id %}
                <div class="actions">
                    <a class="btn" href="/chat/{{ profile_user.id }}">إرسال رسالة</a>
                    <form method="post" action="/follow/{{ profile_user.id }}">
                        <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
                        <button class="btn-light">{{ 'إلغاء المتابعة' if is_following else 'متابعة' }}</button>
                    </form>
                </div>
                {% endif %}
            </div>
        </div>

        <h2 class="page-title">مقالات العضو</h2>

        {% for a in articles %}
        <div class="card article-card">
            {% if a.image %}<img class="post-media" src="/uploads/{{ a.image }}">{% endif %}
            {% if a.video %}<video class="post-media" controls preload="metadata"><source src="/uploads/{{ a.video }}"></video>{% endif %}

            <div class="article-inner">
                <h3><a href="/article/{{ a.id }}">{{ a.title }}</a> <span class="category-badge">{{ a.category }}</span></h3>
                <p class="small">{{ a.created_at }} | 👁️ {{ a.views }}</p>
                <p class="article-content">{{ a.content[:500] }}{% if a.content|length > 500 %}...{% endif %}</p>
            </div>
        </div>
        {% else %}
        <div class="card empty">لا توجد مقالات.</div>
        {% endfor %}
    </div>
    """, user=me, profile_user=profile_user, articles=articles, followers_count=followers_count, following_count=following_count, is_following=is_following)


@app.route("/delete_article/<int:article_id>", methods=["POST"])
def delete_article(article_id):
    user, response = login_required()
    if response:
        return response

    con = db()
    article = con.execute("SELECT user_id, image, video FROM articles WHERE id=?", (article_id,)).fetchone()

    if not article or article["user_id"] != user["id"]:
        con.close()
        return message_page("غير مصرح", "لا تملك صلاحية حذف هذا المقال.", 403, True)

    make_backup("before_delete_article")
    delete_upload(article["image"])
    delete_upload(article["video"])

    con.execute("DELETE FROM articles WHERE id=?", (article_id,))
    con.commit()
    con.close()

    return redirect(request.referrer or "/")


@app.route("/delete_comment/<int:comment_id>", methods=["POST"])
def delete_comment(comment_id):
    user, response = login_required()
    if response:
        return response

    con = db()
    comment = con.execute("""
        SELECT comments.*, articles.user_id AS article_owner
        FROM comments
        JOIN articles ON articles.id=comments.article_id
        WHERE comments.id=?
    """, (comment_id,)).fetchone()

    if not comment or (user["id"] != comment["user_id"] and user["id"] != comment["article_owner"]):
        con.close()
        return message_page("غير مصرح", "لا تملك صلاحية حذف هذا التعليق.", 403, True)

    article_id = comment["article_id"]
    con.execute("DELETE FROM comments WHERE id=?", (comment_id,))
    con.commit()
    con.close()

    return redirect(f"/article/{article_id}")


@app.route("/hashtag/<tag>")
def hashtag_page(tag):
    tag = re.sub(r"[^\w\u0600-\u06FF]", "", tag.lower())
    tag = safe_text(tag, 40)

    user = current_user()

    con = db()
    articles = con.execute("""
        SELECT articles.*, users.username, users.full_name, users.avatar, users.last_seen,
        (SELECT COUNT(*) FROM likes WHERE likes.article_id=articles.id) AS likes_count,
        (SELECT COUNT(*) FROM comments WHERE comments.article_id=articles.id) AS comments_count
        FROM articles
        JOIN users ON users.id=articles.user_id
        JOIN article_hashtags ON article_hashtags.article_id=articles.id
        JOIN hashtags ON hashtags.id=article_hashtags.hashtag_id
        WHERE hashtags.tag=?
        ORDER BY articles.id DESC
    """, (tag,)).fetchall()
    con.close()

    return render_page("""
    <div class="container">
        <div class="card"><h2 class="form-title">منشورات الوسم #{{ tag }}</h2></div>

        {% for a in articles %}
        <div class="card article-card">
            {% if a.image %}<img class="post-media" src="/uploads/{{ a.image }}">{% endif %}
            {% if a.video %}<video class="post-media" controls preload="metadata"><source src="/uploads/{{ a.video }}"></video>{% endif %}

            <div class="article-inner">
                <h3><a href="/article/{{ a.id }}">{{ a.title }}</a> <span class="category-badge">{{ a.category }}</span></h3>
                <p class="small">بواسطة: <a href="/user/{{ a.user_id }}">{{ a.full_name or a.username }}</a> | {{ a.created_at }} | 👁️ {{ a.views }}</p>
                <p class="article-content">{{ a.content[:700] }}{% if a.content|length > 700 %}...{% endif %}</p>
                <div class="actions"><a class="btn btn-light" href="/article/{{ a.id }}">قراءة كاملة</a></div>
            </div>
        </div>
        {% else %}
        <div class="card empty">لا توجد منشورات بهذا الوسم.</div>
        {% endfor %}
    </div>
    """, user=user, articles=articles, tag=tag)


@app.route("/save_article/<int:article_id>", methods=["POST"])
def save_article(article_id):
    user, response = login_required()
    if response:
        return response

    con = db()

    article = con.execute("SELECT id FROM articles WHERE id=?", (article_id,)).fetchone()
    if not article:
        con.close()
        return message_page("غير موجود", "المقال غير موجود.", 404, True)

    existing = con.execute(
        "SELECT 1 FROM saved_articles WHERE user_id=? AND article_id=?",
        (user["id"], article_id)
    ).fetchone()

    if existing:
        con.execute("DELETE FROM saved_articles WHERE user_id=? AND article_id=?", (user["id"], article_id))
    else:
        con.execute(
            "INSERT INTO saved_articles(user_id,article_id,created_at) VALUES(?,?,datetime('now','localtime'))",
            (user["id"], article_id)
        )

    con.commit()
    con.close()

    return redirect(request.referrer or "/")


@app.route("/saved")
def saved_articles():
    user, response = login_required()
    if response:
        return response

    con = db()
    articles = con.execute("""
        SELECT articles.*, users.username, users.full_name
        FROM saved_articles
        JOIN articles ON articles.id=saved_articles.article_id
        JOIN users ON users.id=articles.user_id
        WHERE saved_articles.user_id=?
        ORDER BY saved_articles.created_at DESC
    """, (user["id"],)).fetchall()
    con.close()

    return render_page("""
    <div class="container">
        <h2 class="page-title">المقالات المحفوظة</h2>

        {% for a in articles %}
        <div class="card">
            <h3><a href="/article/{{ a.id }}">{{ a.title }}</a></h3>
            <p class="small">بواسطة: {{ a.full_name or a.username }} | {{ a.created_at }}</p>
            <p class="article-content">{{ a.content[:500] }}{% if a.content|length > 500 %}...{% endif %}</p>
            <a class="btn btn-light" href="/article/{{ a.id }}">فتح</a>
        </div>
        {% else %}
        <div class="card empty">لا توجد مقالات محفوظة.</div>
        {% endfor %}
    </div>
    """, user=user, articles=articles)


@app.route("/follow/<int:user_id>", methods=["POST"])
def follow_user(user_id):
    user, response = login_required()
    if response:
        return response

    if user_id == user["id"]:
        return redirect(request.referrer or "/")

    con = db()

    target = con.execute("SELECT id FROM users WHERE id=?", (user_id,)).fetchone()
    if not target:
        con.close()
        return message_page("غير موجود", "الحساب غير موجود.", 404, True)

    existing = con.execute(
        "SELECT 1 FROM follows WHERE follower_id=? AND following_id=?",
        (user["id"], user_id)
    ).fetchone()

    if existing:
        con.execute("DELETE FROM follows WHERE follower_id=? AND following_id=?", (user["id"], user_id))
    else:
        con.execute(
            "INSERT INTO follows(follower_id, following_id, created_at) VALUES(?,?,datetime('now','localtime'))",
            (user["id"], user_id)
        )

    con.commit()
    con.close()

    return redirect(request.referrer or f"/user/{user_id}")


@app.route("/backup_now")
def backup_now():
    user, response = login_required()
    if response:
        return response

    name = make_backup("manual")

    if not name:
        return message_page("تعذر النسخ", "لم أتمكن من إنشاء نسخة احتياطية.", 500, True)

    return message_page("تم النسخ", f"تم إنشاء نسخة احتياطية: {name}")


@app.route("/about")
def about():
    return render_page("""
    <div class="container">
        <section class="hero">
            <div class="hero-content">
                <img class="hero-logo" src="{{ logo_url }}" alt="طرح أفكار">
                <div>
                    <h1>عن منصة طرح أفكار</h1>
                    <p>منصة عربية لنشر المقالات والأفكار، فيها حسابات، بروفايلات، تعليقات، إعجابات، مشاهدات، فيديوهات، محادثات خاصة، وحالة أونلاين.</p>
                </div>
            </div>
        </section>

        <div class="card">
            <h2 class="form-title">التخزين الآمن</h2>
            <p>البيانات والملفات محفوظة في مجلد دائم خارج مجلد المشروع.</p>
            <p class="small">التخزين الحالي: {{ data_dir }}</p>
        </div>
    </div>
    """, data_dir=DATA_DIR)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = normalize_username(request.form.get("username"))
        full_name = safe_text(request.form.get("full_name"), 60)
        password = request.form.get("password", "")

        if len(username) < 3 or len(password) < 6:
            return message_page("خطأ", "اسم المستخدم 3 أحرف على الأقل، وكلمة المرور 6 أحرف على الأقل.", 400, True)

        make_backup("before_register")

        con = db()
        try:
            con.execute("""
                INSERT INTO users(username, full_name, password, created_at, last_seen)
                VALUES(?, ?, ?, datetime('now','localtime'), ?)
            """, (username, full_name, generate_password_hash(password), int(time.time())))
            con.commit()
        except sqlite3.IntegrityError:
            con.close()
            return message_page("اسم موجود", "اسم المستخدم موجود من قبل.", 409, True)

        con.close()
        return redirect("/login")

    return render_page("""
    <div class="container">
        <section class="hero">
            <div class="hero-content">
                <img class="hero-logo" src="{{ logo_url }}" alt="طرح أفكار">
                <div>
                    <h1>إنشاء حساب جديد</h1>
                    <p>انضم للمنصة وابدأ بنشر أفكارك ومقالاتك.</p>
                </div>
            </div>
        </section>

        <div class="card">
            <form method="post">
                <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
                <input name="full_name" maxlength="60" placeholder="الاسم الظاهر اختياري">
                <input name="username" maxlength="30" placeholder="اسم المستخدم" required>
                <input name="password" type="password" placeholder="كلمة المرور" required>
                <button>تسجيل</button>
            </form>

            <p><a href="/login">عندي حساب</a></p>
        </div>
    </div>
    """)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = normalize_username(request.form.get("username"))
        password = request.form.get("password", "")

        con = db()
        user = con.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        con.close()

        if user and check_password_hash(user["password"], password):
            session.clear()
            session.permanent = True
            session["user_id"] = user["id"]
            generate_csrf_token()
            current_user(update_seen=True)
            return redirect("/")

        time.sleep(1.5)
        return message_page("فشل الدخول", "بيانات الدخول غير صحيحة.", 401, True)

    return render_page("""
    <div class="container">
        <section class="hero">
            <div class="hero-content">
                <img class="hero-logo" src="{{ logo_url }}" alt="طرح أفكار">
                <div>
                    <h1>تسجيل الدخول</h1>
                    <p>ادخل لحسابك وتابع أفكارك ومقالاتك.</p>
                </div>
            </div>
        </section>

        <div class="card">
            <form method="post">
                <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
                <input name="username" placeholder="اسم المستخدم" required>
                <input name="password" type="password" placeholder="كلمة المرور" required>
                <button>دخول</button>
            </form>

            <p><a href="/register">إنشاء حساب جديد</a></p>
        </div>
    </div>
    """)


@app.route("/profile", methods=["GET", "POST"])
def profile():
    user, response = login_required()
    if response:
        return response

    if request.method == "POST":
        full_name = safe_text(request.form.get("full_name"), 60)
        bio = safe_text(request.form.get("bio"), 300)
        avatar = save_image(request.files.get("avatar"))

        if avatar == "__BAD_TYPE__":
            return message_page("نوع صورة غير مدعوم", "ارفع صورة png أو jpg أو jpeg أو gif أو webp.", 400, True)

        make_backup("before_profile")

        con = db()

        if avatar:
            old = con.execute("SELECT avatar FROM users WHERE id=?", (user["id"],)).fetchone()
            if old and old["avatar"]:
                delete_upload(old["avatar"])

            con.execute(
                "UPDATE users SET full_name=?, bio=?, avatar=? WHERE id=?",
                (full_name, bio, avatar, user["id"])
            )
        else:
            con.execute(
                "UPDATE users SET full_name=?, bio=? WHERE id=?",
                (full_name, bio, user["id"])
            )

        con.commit()
        con.close()

        return redirect("/profile")

    return render_page("""
    <div class="container">
        <div class="card">
            <h2 class="form-title">تعديل البروفايل</h2>

            <div class="profile-row">
                {% if user.avatar %}<img class="avatar-big" src="/uploads/{{ user.avatar }}">{% else %}<div class="avatar-big"></div>{% endif %}
                <div><b>{{ user.username }}</b><p class="small">{{ online_label(user) }}</p></div>
            </div>

            <form method="post" enctype="multipart/form-data">
                <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
                <input name="full_name" maxlength="60" placeholder="الاسم الظاهر" value="{{ user.full_name or '' }}">
                <textarea name="bio" maxlength="300" rows="4" placeholder="نبذة قصيرة">{{ user.bio or '' }}</textarea>
                <input type="file" name="avatar" accept="image/png,image/jpeg,image/gif,image/webp">
                <button>حفظ التغييرات</button>
            </form>
        </div>
    </div>
    """, user=user)


@app.route("/users")
def users():
    user = current_user()
    q = request.args.get("q", "").strip()

    con = db()

    if q:
        p = f"%{q}%"
        rows = con.execute(
            "SELECT * FROM users WHERE username LIKE ? OR full_name LIKE ? ORDER BY last_seen DESC LIMIT 100",
            (p, p)
        ).fetchall()
    else:
        rows = con.execute(
            "SELECT * FROM users ORDER BY last_seen DESC, id DESC LIMIT 100"
        ).fetchall()

    con.close()

    return render_page("""
    <div class="container">
        <form method="get" class="card searchbar">
            <input name="q" placeholder="ابحث عن عضو" value="{{ q }}">
            <button>بحث</button>
        </form>

        {% for u in rows %}
        <div class="card profile-row">
            {% if u.avatar %}<img class="avatar" src="/uploads/{{ u.avatar }}">{% else %}<div class="avatar"></div>{% endif %}

            <div style="flex:1">
                <h3 style="margin:0"><a href="/user/{{ u.id }}">{{ u.full_name or u.username }}</a></h3>
                <p class="small">@{{ u.username }} | <span class="{{ 'online' if is_online(u) else 'offline' }}">{{ online_label(u) }}</span></p>
                <p>{{ u.bio or '' }}</p>
            </div>

            {% if user and user.id != u.id %}
                <a class="btn" href="/chat/{{ u.id }}">مراسلة</a>
            {% endif %}
        </div>
        {% endfor %}
    </div>
    """, user=user, rows=rows, q=q)


@app.route("/like/<int:article_id>", methods=["POST"])
def like(article_id):
    user, response = login_required()
    if response:
        return response

    con = db()
    article = con.execute("SELECT id FROM articles WHERE id=?", (article_id,)).fetchone()

    if not article:
        con.close()
        return message_page("خطأ", "المقال غير موجود.", 404, True)

    try:
        con.execute("INSERT INTO likes(article_id,user_id) VALUES(?,?)", (article_id, user["id"]))
    except sqlite3.IntegrityError:
        con.execute("DELETE FROM likes WHERE article_id=? AND user_id=?", (article_id, user["id"]))

    con.commit()
    con.close()

    return redirect(request.referrer or "/")


@app.route("/comment/<int:article_id>", methods=["POST"])
def comment(article_id):
    user, response = login_required()
    if response:
        return response

    text = safe_text(request.form.get("comment"), 300)
    if not text:
        return redirect(request.referrer or "/")

    con = db()
    article = con.execute("SELECT id FROM articles WHERE id=?", (article_id,)).fetchone()

    if article:
        con.execute("""
            INSERT INTO comments(article_id,user_id,comment,created_at)
            VALUES(?,?,?,datetime('now','localtime'))
        """, (article_id, user["id"], text))
        con.commit()

    con.close()

    return redirect(request.referrer or f"/article/{article_id}")


@app.route("/messages")
def messages():
    user, response = login_required()
    if response:
        return response

    con = db()
    conversations = con.execute("""
        SELECT u.*,
        (SELECT body FROM messages m WHERE (m.sender_id=u.id AND m.receiver_id=?) OR (m.sender_id=? AND m.receiver_id=u.id) ORDER BY m.id DESC LIMIT 1) AS last_message,
        (SELECT created_at FROM messages m WHERE (m.sender_id=u.id AND m.receiver_id=?) OR (m.sender_id=? AND m.receiver_id=u.id) ORDER BY m.id DESC LIMIT 1) AS last_time,
        (SELECT COUNT(*) FROM messages m WHERE m.sender_id=u.id AND m.receiver_id=? AND m.is_read=0) AS unread
        FROM users u
        WHERE u.id != ?
        AND EXISTS(
            SELECT 1 FROM messages m
            WHERE (m.sender_id=u.id AND m.receiver_id=?)
            OR (m.sender_id=? AND m.receiver_id=u.id)
        )
        ORDER BY last_time DESC
    """, (
        user["id"], user["id"],
        user["id"], user["id"],
        user["id"],
        user["id"],
        user["id"], user["id"]
    )).fetchall()
    con.close()

    return render_page("""
    <div class="container">
        <div class="card">
            <h2 class="form-title">المحادثات</h2>
            <a class="btn btn-light" href="/users">ابدأ محادثة من صفحة الأعضاء</a>
        </div>

        {% for c in conversations %}
        <div class="card profile-row">
            {% if c.avatar %}<img class="avatar" src="/uploads/{{ c.avatar }}">{% else %}<div class="avatar"></div>{% endif %}

            <div style="flex:1">
                <h3 style="margin:0">
                    <a href="/chat/{{ c.id }}">{{ c.full_name or c.username }}</a>
                    {% if c.unread %}<span class="badge">{{ c.unread }}</span>{% endif %}
                </h3>
                <p class="small"><span class="{{ 'online' if is_online(c) else 'offline' }}">{{ online_label(c) }}</span> | {{ c.last_time }}</p>
                <p>{{ c.last_message }}</p>
            </div>

            <a class="btn" href="/chat/{{ c.id }}">فتح</a>
        </div>
        {% else %}
        <div class="card empty">ما عندك محادثات حالياً.</div>
        {% endfor %}
    </div>
    """, user=user, conversations=conversations)


@app.route("/chat/<int:other_id>", methods=["GET", "POST"])
def chat(other_id):
    user, response = login_required()
    if response:
        return response

    if other_id == user["id"]:
        return redirect("/messages")

    con = db()
    other = con.execute("SELECT * FROM users WHERE id=?", (other_id,)).fetchone()

    if not other:
        con.close()
        return message_page("غير موجود", "هذا العضو غير موجود.", 404, True)

    if request.method == "POST":
        body = safe_text(request.form.get("body"), 1000)

        if body:
            con.execute("""
                INSERT INTO messages(sender_id,receiver_id,body,created_at)
                VALUES(?,?,?,datetime('now','localtime'))
            """, (user["id"], other_id, body))
            con.commit()

        con.close()
        return redirect(f"/chat/{other_id}")

    con.execute("UPDATE messages SET is_read=1 WHERE sender_id=? AND receiver_id=?", (other_id, user["id"]))
    con.commit()

    msgs = con.execute("""
        SELECT * FROM messages
        WHERE (sender_id=? AND receiver_id=?)
        OR (sender_id=? AND receiver_id=?)
        ORDER BY id ASC
    """, (user["id"], other_id, other_id, user["id"])).fetchall()

    con.close()

    return render_page("""
    <div class="container">
        <div class="card">
            <div class="profile-row">
                {% if other.avatar %}<img class="avatar" src="/uploads/{{ other.avatar }}">{% else %}<div class="avatar"></div>{% endif %}
                <div>
                    <h2 style="margin:0">محادثة مع {{ other.full_name or other.username }}</h2>
                    <p class="small"><span class="{{ 'online' if is_online(other) else 'offline' }}">{{ online_label(other) }}</span></p>
                </div>
            </div>
        </div>

        <div class="card">
            <div class="chat-box" id="chatBox">
                {% for m in msgs %}
                <div class="message {{ 'mine' if m.sender_id == user.id else 'theirs' }}">
                    {{ m.body }}
                    <div class="small" style="color:inherit;opacity:.8">{{ m.created_at }}</div>
                </div>
                {% else %}
                <p class="small">ابدأ المحادثة برسالة.</p>
                {% endfor %}
            </div>

            <form method="post" class="searchbar" style="margin-top:10px">
                <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
                <input name="body" maxlength="1000" placeholder="اكتب رسالة" required>
                <button>إرسال</button>
            </form>
        </div>
    </div>

    <script>
    var box = document.getElementById('chatBox');
    if (box) { box.scrollTop = box.scrollHeight; }
    </script>
    """, user=user, other=other, msgs=msgs)


@app.route("/api/online")
def api_online():
    current_user()

    con = db()
    rows = con.execute("SELECT id, username, full_name, last_seen FROM users ORDER BY last_seen DESC LIMIT 50").fetchall()
    con.close()

    return jsonify([
        {"id": r["id"], "name": r["full_name"] or r["username"], "online": is_online(r)}
        for r in rows
    ])


@app.route("/uploads/<path:filename>")
def uploads(filename):
    filename = os.path.basename(filename)
    return send_from_directory(UPLOAD_FOLDER, filename)


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    lan_ip = get_lan_ip()

    print("\n==============================")
    print("منصة طرح الأفكار اشتغلت ✅")
    print(f"افتح من نفس الجهاز: http://127.0.0.1:{port}")
    print(f"افتح من جهاز ثاني على نفس الواي فاي: http://{lan_ip}:{port}")
    print(f"DATA_DIR: {DATA_DIR}")
    print(f"قاعدة البيانات: {DB_PATH}")
    print(f"مجلد الملفات: {UPLOAD_FOLDER}")
    print(f"مجلد النسخ الاحتياطية: {BACKUP_FOLDER}")
    print("لإيقاف السيرفر اضغط CTRL + C")
    print("==============================\n")

    app.run(host="0.0.0.0", port=port, debug=False)