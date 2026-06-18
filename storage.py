import os
import sqlite3
import time

class DatabaseManager:
    """
    مدير قاعدة البيانات: مسؤول عن الاتصال، إنشاء الجداول، والنسخ الاحتياطي الآمن.
    """
    def __init__(self, db_path="data/tarh_afkar.db", backup_dir="data/backups", max_backups=25):
        self.db_path = db_path
        self.backup_dir = backup_dir
        self.max_backups = max_backups
        
        # إنشاء المجلدات إذا لم تكن موجودة
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        os.makedirs(self.backup_dir, exist_ok=True)

    def get_connection(self):
        """
        يفتح اتصالاً قوياً بقاعدة البيانات مع تفعيل الحماية من الانهيار.
        """
        # timeout=20.0: يمنع خطأ "database is locked" عند الضغط العالي
        con = sqlite3.connect(self.db_path, timeout=20.0)
        
        # لجلب البيانات على شكل قواميس (Dictionaries) بدلاً من مصفوفات عادية
        con.row_factory = sqlite3.Row
        
        # تفعيل القيود بين الجداول (Foreign Keys)
        con.execute("PRAGMA foreign_keys = ON")
        
        # تفعيل وضع WAL (Write-Ahead Logging) لعمليات قراءة/كتابة متزامنة وسريعة جداً
        con.execute("PRAGMA journal_mode = WAL")
        con.execute("PRAGMA synchronous = NORMAL")
        
        return con

    def init_database(self):
        """
        إنشاء هيكل جداول المنصة (إذا لم تكن موجودة).
        """
        con = self.get_connection()
        try:
            con.executescript("""
            CREATE TABLE IF NOT EXISTS users(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                full_name TEXT DEFAULT '',
                bio TEXT DEFAULT '',
                avatar TEXT,
                last_seen INTEGER DEFAULT 0,
                created_at TEXT DEFAULT ''
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

            CREATE TABLE IF NOT EXISTS comments(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                article_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                comment TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(article_id) REFERENCES articles(id) ON DELETE CASCADE,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            
            -- يمكنك إضافة باقي الجداول هنا (likes, messages, hashtags... الخ)
            """)
            
            # إنشاء الفهارس (Indexes) لتسريع البحث
            con.execute("CREATE INDEX IF NOT EXISTS idx_articles_user ON articles(user_id)")
            con.execute("CREATE INDEX IF NOT EXISTS idx_articles_category ON articles(category)")
            
            con.commit()
            print("✅ تم إنشاء أو تحديث جداول قاعدة البيانات بنجاح.")
        except Exception as e:
            print(f"❌ حدث خطأ أثناء بناء القاعدة: {e}")
        finally:
            con.close()

    def make_backup(self, reason="auto"):
        """
        أخذ نسخة احتياطية آمنة لا تتلف البيانات حتى وإن كانت القاعدة قيد الاستخدام.
        """
        if not os.path.exists(self.db_path):
            return None
            
        stamp = time.strftime("%Y%m%d_%H%M%S")
        name = f"backup_{reason}_{stamp}.db"
        target_path = os.path.join(self.backup_dir, name)
        
        try:
            # استخدام API النسخ المدمج في SQLite لنسخ آمن 100%
            source_con = self.get_connection()
            backup_con = sqlite3.connect(target_path)
            
            with backup_con:
                source_con.backup(backup_con)
                
            backup_con.close()
            source_con.close()

            # حذف النسخ القديمة إذا تجاوزت الحد الأقصى (MAX_BACKUPS)
            backups = sorted(
                [os.path.join(self.backup_dir, f) for f in os.listdir(self.backup_dir) if f.endswith(".db")],
                key=os.path.getmtime,
                reverse=True
            )
            for old_backup in backups[self.max_backups:]:
                os.remove(old_backup)
                
            return name
        except Exception as e:
            print(f"❌ فشل النسخ الاحتياطي: {e}")
            return None

    def execute_query(self, query, params=()):
        """
        دالة مساعدة لتنفيذ أوامر الإدخال والتعديل والحذف (INSERT, UPDATE, DELETE).
        """
        con = self.get_connection()
        try:
            cur = con.execute(query, params)
            con.commit()
            return cur.lastrowid
        finally:
            con.close()

    def fetch_all(self, query, params=()):
        """
        دالة مساعدة لجلب مجموعة من البيانات (SELECT).
        """
        con = self.get_connection()
        try:
            return con.execute(query, params).fetchall()
        finally:
            con.close()

    def fetch_one(self, query, params=()):
        """
        دالة مساعدة لجلب صف واحد فقط من البيانات.
        """
        con = self.get_connection()
        try:
            return con.execute(query, params).fetchone()
        finally:
            con.close()

# ==========================================
# اختبار مدير التخزين (عند تشغيل الملف مباشرة)
# ==========================================
if __name__ == "__main__":
    # 1. تهيئة الكلاس
    db_manager = DatabaseManager(db_path="test_data/my_app.db", backup_dir="test_data/backups")
    
    # 2. بناء القاعدة
    db_manager.init_database()
    
    # 3. إدخال بيانات تجريبية (استخدام الدالة المساعدة)
    # db_manager.execute_query("INSERT OR IGNORE INTO users (username, password) VALUES (?, ?)", ("admin", "hashed_pass"))
    
    # 4. أخذ نسخة احتياطية
    backup_file = db_manager.make_backup("manual_test")
    if backup_file:
        print(f"✅ تم حفظ النسخة الاحتياطية باسم: {backup_file}")
