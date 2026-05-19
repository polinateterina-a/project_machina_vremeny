from flask import Flask, render_template, jsonify, request, send_from_directory
import sqlite3
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

DB_PATH = 'instance/perekrestok.db'

for folder in ['static/photos/historical', 'static/photos/modern', 'static/audio', 'instance', 'static/thumbnails']:
    os.makedirs(folder, exist_ok=True)

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.executescript('''
        CREATE TABLE IF NOT EXISTS excursions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            duration TEXT DEFAULT '',
            distance TEXT DEFAULT '',
            start_audio TEXT DEFAULT '',
            end_audio TEXT DEFAULT '',
            start_description TEXT DEFAULT '',
            end_description TEXT DEFAULT ''
        );
        
        CREATE TABLE IF NOT EXISTS locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            lat REAL NOT NULL,
            lng REAL NOT NULL,
            address TEXT DEFAULT '',
            historical_photo TEXT DEFAULT '',
            modern_photo TEXT DEFAULT '',
            audio_file TEXT DEFAULT '',
            description TEXT DEFAULT '',
            year TEXT DEFAULT '',
            tags TEXT DEFAULT '',
            short_description TEXT DEFAULT '',
            thumbnail TEXT DEFAULT ''
        );
        
        CREATE TABLE IF NOT EXISTS excursion_locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            excursion_id INTEGER NOT NULL,
            location_id INTEGER NOT NULL,
            order_num INTEGER DEFAULT 0
        );
        
        CREATE VIRTUAL TABLE IF NOT EXISTS locations_fts USING fts5(
            name, description, tags, content='locations', content_rowid='id'
        );
    ''')
    
    c.execute('SELECT COUNT(*) as cnt FROM excursions')
    if c.fetchone()['cnt'] == 0:
        c.execute('''INSERT INTO excursions VALUES (1, 
            'Красноярск исторический: прогулка сквозь время',
            'Пешеходная экскурсия по историческому центру Красноярска. Маршрут включает 4 знаковых места города.',
            '2 часа', '2.5 км',
            'audio/start.mp3', 'audio/end.mp3',
            'Добро пожаловать на экскурсию «Красноярск исторический»! Мы начинаем наше путешествие от Театра имени Пушкина — одного из старейших театров Сибири. За два часа вы перенесётесь в атмосферу дореволюционного Красноярска, увидите уникальные здания и узнаете истории людей, которые создавали этот город.',
            'Вот и подошла к концу наша экскурсия по историческому Красноярску. Мы прошли от театральной жизни до женского образования, от купеческой торговли до врачебного дела. Каждое из этих зданий — не просто архитектурный памятник, а живая история города. Спасибо, что были с нами!')''')
        
        locs = [
            (1, 'Театр имени А.С. Пушкина', 56.0119, 92.8570, 'пр. Мира, 73',
             'photos/historical/theatre_pushkin_old.jpg', 'photos/modern/theatre_pushkin_new.jpg',
             'audio/theatre_pushkin.mp3',
             'Красноярский драматический театр имени А.С. Пушкина — один из старейших театров Сибири, основанный в 1873 году. Изначально театр располагался в деревянном здании, построенном на средства городского общества. В 1902 году для театра было построено новое каменное здание по проекту архитектора Е.С. Павлова в стиле эклектики с элементами модерна.\n\nНа сцене театра выступали многие известные артисты, здесь ставились произведения русской и зарубежной классики. Театр стал центром культурной жизни дореволюционного Красноярска. Интересный факт: в 1898 году в театре выступал великий русский певец Фёдор Шаляпин.',
             '1902', 'театр, культура, архитектура, модерн', 'Старейший театр Сибири', 'thumbnails/theatre_pushkin.jpg'),
            (2, 'Аптека Общества врачей', 56.0108, 92.8537, 'пр. Мира, 52',
             'photos/historical/apteka_old.jpg', 'photos/modern/apteka_new.jpg',
             'audio/apteka.mp3',
             'Аптека Общества врачей Енисейской губернии — уникальное медицинское учреждение, открытое в 1889 году. Общество врачей было создано в Красноярске в 1886 году и объединяло лучших медиков города.\n\nЭто была не просто аптека, а настоящий медицинский центр. Здесь не только продавали лекарства, но и вели приём врачи, работала лаборатория. При аптеке действовала бесплатная лечебница для бедных. Врачи Общества изучали целебные свойства местных растений и внедряли их в медицинскую практику.',
             '1889', 'медицина, аптека, архитектура, здравоохранение', 'Медицинский центр дореволюционного Красноярска', 'thumbnails/apteka.jpg'),
            (3, 'Торговый дом Гадалова', 56.0115, 92.8527, 'пр. Мира, 79',
             'photos/historical/gadalov_old.jpg', 'photos/modern/gadalov_new.jpg',
             'audio/gadalov.mp3',
             'Торговый дом купцов Гадаловых — символ купеческого Красноярска конца XIX века. Династия Гадаловых была одной из богатейших в Енисейской губернии. Основатель династии Николай Герасимович Гадалов начинал с небольшой торговли, а к концу века владел сетью магазинов, золотыми приисками и пароходством.\n\nГлавный торговый дом был построен в 1890-х годах — роскошное трёхэтажное здание с огромными витринами, где продавалось всё. Гадаловы были не только купцами, но и меценатами — жертвовали деньги на строительство школ, больниц, церквей.',
             '1890-е', 'купечество, торговля, архитектура, меценатство', 'Главный торговый центр купцов Гадаловых', 'thumbnails/gadalov.jpg'),
            (4, 'Женская гимназия', 56.0092, 92.8505, 'ул. Ленина, 108',
             'photos/historical/gymnasium_old.jpg', 'photos/modern/gymnasium_new.jpg',
             'audio/gymnasium.mp3',
             'Красноярская женская гимназия — одно из первых учебных заведений для девочек в Сибири, открытое в 1869 году. В 1878 году получило статус гимназии. Обучение длилось 7 лет, выпускницы получали звание домашней учительницы.\n\nВ программу входили Закон Божий, русский язык, математика, история, география, иностранные языки, рукоделие. Гимназия давала лучшее в городе образование для девочек. Здесь учились дочери купцов, чиновников, врачей. Гимназия сыграла огромную роль в развитии женского образования в Сибири.',
             '1869', 'образование, гимназия, архитектура, история', 'Первое учебное заведение для девочек в Сибири', 'thumbnails/gymnasium.jpg')
        ]
        for loc in locs:
            c.execute('''INSERT INTO locations VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)''', loc)
        
        for i in range(1,5):
            c.execute('INSERT INTO excursion_locations VALUES (?,1,?,?)', (i,i,i))
    
    conn.commit()
    conn.close()

init_db()

# ===== МАРШРУТЫ =====

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/search')
def search_page():
    return render_template('search.html')

@app.route('/excursion')
def excursion():
    return render_template('index.html')

@app.route('/admin')
def admin():
    return render_template('admin.html')

@app.route('/api/search')
def api_search():
    q = request.args.get('q', '')
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    if q and len(q) >= 2:
        try:
            results = c.execute('''SELECT l.* FROM locations l
                                   JOIN locations_fts fts ON l.id = fts.rowid
                                   WHERE locations_fts MATCH ?
                                   ORDER BY rank LIMIT 10''', (q,)).fetchall()
        except:
            results = c.execute('''SELECT * FROM locations 
                                   WHERE name LIKE ? OR description LIKE ? OR tags LIKE ?
                                   LIMIT 10''', (f'%{q}%', f'%{q}%', f'%{q}%')).fetchall()
    else:
        results = []
    
    excursions = c.execute('SELECT * FROM excursions WHERE name LIKE ? OR description LIKE ?',
                          (f'%{q}%', f'%{q}%')).fetchall() if q and len(q) >= 2 else c.execute('SELECT * FROM excursions').fetchall()
    
    conn.close()
    return jsonify({
        'locations': [dict(r) for r in results],
        'excursions': [dict(e) for e in excursions]
    })

@app.route('/api/excursions/1/locations')
def get_excursion_data():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    ex = c.execute('SELECT * FROM excursions WHERE id=1').fetchone()
    locs = c.execute('''SELECT l.* FROM locations l 
                        JOIN excursion_locations el ON l.id=el.location_id 
                        WHERE el.excursion_id=1 ORDER BY el.order_num''').fetchall()
    conn.close()
    return jsonify({'excursion': dict(ex), 'locations': [dict(l) for l in locs]})

@app.route('/api/locations/<int:lid>')
def get_location(lid):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    loc = conn.execute('SELECT * FROM locations WHERE id=?', (lid,)).fetchone()
    conn.close()
    return jsonify(dict(loc)) if loc else ('Not found', 404)

@app.route('/api/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'Нет файла'}), 400
    file = request.files['file']
    folder = request.form.get('folder', 'photos/modern')
    if file.filename == '':
        return jsonify({'error': 'Файл не выбран'}), 400
    filename = secure_filename(file.filename)
    save_path = os.path.join('static', folder, filename)
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    file.save(save_path)
    return jsonify({'path': f'{folder}/{filename}', 'message': 'Файл загружен'})

@app.route('/api/excursions', methods=['GET', 'POST'])
def excursions_handler():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    if request.method == 'POST':
        data = request.get_json()
        c = conn.cursor()
        c.execute('INSERT INTO excursions (name, description, duration, distance) VALUES (?,?,?,?)',
                  (data['name'], data.get('description',''), data.get('duration',''), data.get('distance','')))
        conn.commit()
        eid = c.lastrowid
        conn.close()
        return jsonify({'id': eid})
    else:
        exs = conn.execute('SELECT * FROM excursions').fetchall()
        conn.close()
        return jsonify([dict(e) for e in exs])

@app.route('/api/locations', methods=['GET', 'POST'])
def locations_handler():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    if request.method == 'POST':
        data = request.get_json()
        c = conn.cursor()
        c.execute('''INSERT INTO locations (name, lat, lng, address, historical_photo, modern_photo,
                     audio_file, description, year, tags, short_description, thumbnail)
                     VALUES (?,?,?,?,?,?,?,?,?,?,?,?)''',
                  (data['name'], data['lat'], data['lng'], data.get('address',''),
                   data.get('historical_photo',''), data.get('modern_photo',''),
                   data.get('audio_file',''), data.get('description',''),
                   data.get('year',''), data.get('tags',''), data.get('short_description',''),
                   data.get('thumbnail','')))
        conn.commit()
        lid = c.lastrowid
        conn.close()
        return jsonify({'id': lid})
    else:
        locs = conn.execute('SELECT * FROM locations').fetchall()
        conn.close()
        return jsonify([dict(l) for l in locs])

@app.route('/api/excursions/<int:eid>/locations', methods=['POST'])
def add_loc_to_exc(eid):
    data = request.get_json()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('INSERT INTO excursion_locations (excursion_id, location_id, order_num) VALUES (?,?,?)',
              (eid, data['location_id'], data.get('order_num',0)))
    conn.commit()
    conn.close()
    return jsonify({'message': 'OK'})

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

#if __name__ == '__main__':
    import socket
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    
    print('='*50)
    print('Перекрёсток эпох — сервер запущен')
    print(f'Локально:     http://127.0.0.1:5000')
    print(f'В сети:       http://{local_ip}:5000')
    print(f'Админ:        http://{local_ip}:5000/admin')
    print('Открывайте эти адреса на других устройствах')
    print('='*50)
    app.run(debug=False, host='0.0.0.0', port=5000)
if __name__ == '__main__':
    print('='*50)
    print('Перекрёсток эпох — сервер запущен')
    print('Главная: http://127.0.0.1:5000')
    print('Поиск: http://127.0.0.1:5000/search')
    print('Админ: http://127.0.0.1:5000/admin')
    print('='*50)
    app.run(debug=True, host='127.0.0.1', port=5000)