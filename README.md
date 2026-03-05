# משחק זיכרון NDFA

משחק זיכרון רב-משתתפים (1–3) עם פעילויות נוירו-התפתחותיות־תפקודיות בכל התאמה.

## סטק

- **Backend:** Flask + Flask-SocketIO + Flask-SQLAlchemy
- **Frontend:** React (Vite)
- **DB:** PostgreSQL

## דרישות

- Python 3.10+
- Node.js 18+
- PostgreSQL

## התקנה והרצה

### 1. מסד נתונים PostgreSQL

צור מסד נתונים:

```bash
createdb ndfa_memory_game
```

או ב-pgAdmin / SQL:

```sql
CREATE DATABASE ndfa_memory_game;
```

### 2. Backend (Flask)

```bash
cd backend
python -m venv venv
venv\Scripts\activate   # Windows
# source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

צור קובץ `.env` בתיקיית `backend` (העתק מ-`.env.example`):

```
DATABASE_URL=postgresql://USER:PASSWORD@localhost:5432/ndfa_memory_game
```

הרץ את השרת:

```bash
python app.py
```

השרת יעלה על `http://127.0.0.1:5000`. טבלאות נוצרות אוטומטית בהרצה ראשונה.

### 3. Frontend (React)

בשורש הפרויקט:

```bash
npm install
npm run dev
```

האפליקציה תפתח ב-`http://localhost:5173` עם פרוקסי ל-API ול-Socket.IO.

## זרימת משחק

1. **התחברות:** הזנת אימייל ושם (נשמר במערכת).
2. **לובי:** יצירת חדר (בחירת 1/2/3 שחקנים) או הצטרפות לחדר (רשימת חדרים או קוד חדר).
3. **חדר:** מחכים עד שמספר השחקנים מתאים; בעל החדר לוחץ "התחל משחק".
4. **משחק:** תורות – כל שחקן הופך שני קלפים. בהתאמה נפתחת פעילות מהקטגוריה של הזוג (וסטיבולרי, טקטילי, פרופריוצפטיבי וכו').
5. **סיום פעילות:** לוחצים "סיימתי את הפעילות" וחוזרים למשחק.

## קטגוריות פעילויות

סטיבולרי, טקטילי, פרופריוצפטיבי, בידול אצבעות, חציית קו אמצע, שרירי עיניים, טונוס, הצלבה, שמיעה, קשר עין–יד.
