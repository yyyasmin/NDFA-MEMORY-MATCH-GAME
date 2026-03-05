import os
import random
import string
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room, leave_room
import time
from config import Config
from models import db, Player, Room, RoomPlayer

app = Flask(__name__)
app.config.from_object(Config)
# CORS: allow Netlify frontend explicitly so cross-origin from Netlify is never blocked.
_cors_origins = os.environ.get('CORS_ORIGINS', '').strip() or '*'
_origins_list = [o.strip() for o in _cors_origins.split(',') if o.strip()] if _cors_origins != '*' else ['*']
if '*' not in _origins_list:
    _origins_list.append('https://ndfa-memory-match-game.netlify.app')
CORS(app, origins=_origins_list)
db.init_app(app)
_socket_cors = _origins_list if _origins_list != ['*'] else '*'
socketio = SocketIO(app, cors_allowed_origins=_socket_cors)

ROOMS_IN_MEMORY = {}
SOCKET_PLAYER = {}

def generate_room_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

def get_categories():
    return [
        'vestibular', 'tactile', 'proprioceptive', 'differentiation',
        'midline', 'eyeMuscles', 'tone', 'crossing', 'hearing', 'eyeHand'
    ]

def create_shuffled_deck(pair_count):
    categories = get_categories()
    deck = []
    for i in range(pair_count):
        cat = categories[i % len(categories)]
        deck.append({'id': i * 2, 'pairId': i, 'category': cat})
        deck.append({'id': i * 2 + 1, 'pairId': i, 'category': cat})
    random.shuffle(deck)
    return deck

@app.route('/')
def index():
    return jsonify({'service': 'NDFA Memory Game API', 'health': '/api/health'})

@app.route('/api/health')
def health():
    return jsonify({'status': 'ok'})

@app.route('/api/players', methods=['POST'])
def register_player():
    data = request.get_json() or {}
    email = (data.get('email') or '').strip()
    nickname = (data.get('nickname') or '').strip()
    if not email or not nickname:
        return jsonify({'error': 'אימייל ושם חובה'}), 400
    player = Player.query.filter_by(email=email).first()
    if player:
        player.nickname = nickname
        db.session.commit()
        return jsonify(player.to_dict())
    player = Player(email=email, nickname=nickname)
    db.session.add(player)
    db.session.commit()
    return jsonify(player.to_dict())

@app.route('/api/rooms', methods=['GET'])
def list_rooms():
    rooms = Room.query.filter_by(status='waiting').all()
    return jsonify([{
        'roomId': r.code,
        'code': r.code,
        'maxPlayers': r.max_players,
        'players': [{'nickname': rp.player.nickname} for rp in r.room_players]
    } for r in rooms])

@app.cli.command()
def init_db():
    db.create_all()

@socketio.on('connect')
def on_connect():
    pass

@socketio.on('register')
def on_register(data):
    sid = request.sid
    email = (data.get('email') or '').strip() if data else ''
    nickname = (data.get('nickname') or '').strip() if data else ''
    if not email or not nickname:
        emit('error', {'message': 'אימייל ושם חובה'})
        return
    player = Player.query.filter_by(email=email).first()
    if not player:
        player = Player(email=email, nickname=nickname)
        db.session.add(player)
        db.session.commit()
    else:
        player.nickname = nickname
        db.session.commit()
    SOCKET_PLAYER[sid] = {'email': email, 'nickname': nickname, 'player_id': player.id}
    emit('registered', {'player': player.to_dict()})

@socketio.on('createRoom')
def on_create_room(data):
    sid = request.sid
    stored = SOCKET_PLAYER.get(sid, {})
    email = (data.get('email') or stored.get('email') or '').strip()
    nickname = (data.get('nickname') or stored.get('nickname') or '').strip()
    if not email or not nickname:
        emit('error', {'message': 'נא להזין אימייל ושם קודם'})
        return
    else:
        player = Player.query.filter_by(email=email).first()
        if not player:
            player = Player(email=email, nickname=nickname)
            db.session.add(player)
            db.session.commit()
        else:
            player.nickname = nickname
            db.session.commit()
    max_players = min(3, max(1, int(data.get('maxPlayers', 1) or 1)))
    code = generate_room_code()
    room_db = Room(code=code, max_players=max_players, host_socket_id=sid)
    db.session.add(room_db)
    db.session.commit()
    SOCKET_PLAYER[sid] = {'email': email, 'nickname': nickname, 'player_id': player.id}
    rp = RoomPlayer(room_id=room_db.id, player_id=player.id, socket_id=sid, score=0)
    db.session.add(rp)
    db.session.commit()
    room_state = {
        'id': code,
        'maxPlayers': max_players,
        'players': [{'id': sid, 'nickname': nickname, 'email': email, 'score': 0}],
        'status': 'waiting',
        'deck': None,
        'flipped': [],
        'scores': {sid: 0},
        'currentTurnIndex': 0,
        'pairCount': 8
    }
    ROOMS_IN_MEMORY[code] = room_state
    join_room(code)
    emit('roomCreated', {'roomId': code, 'room': room_state})
    emit('roomUpdate', room_state, room=code)


@socketio.on('listRooms')
def on_list_rooms():
    """Send list of waiting rooms so second player can see and join."""
    rooms = Room.query.filter_by(status='waiting').all()
    list_ = [{
        'roomId': r.code,
        'code': r.code,
        'maxPlayers': r.max_players,
        'players': [{'nickname': rp.player.nickname} for rp in r.room_players]
    } for r in rooms]
    emit('roomsList', list_)


@socketio.on('joinRoom')
def on_join_room(data):
    sid = request.sid
    room_id = (data.get('roomId') or data.get('code') or '').strip().upper()
    room_db = Room.query.filter_by(code=room_id, status='waiting').first()
    if not room_db:
        emit('error', {'message': 'חדר לא נמצא'})
        return
    if room_db.room_players.count() >= room_db.max_players:
        emit('error', {'message': 'החדר מלא'})
        return
    stored = SOCKET_PLAYER.get(sid, {})
    email = (data.get('email') or stored.get('email') or '').strip()
    nickname = (data.get('nickname') or stored.get('nickname') or '').strip()
    if not email or not nickname:
        emit('error', {'message': 'נא להזין אימייל ושם קודם'})
        return
    player = Player.query.filter_by(email=email).first()
    if not player:
        player = Player(email=email, nickname=nickname)
        db.session.add(player)
        db.session.commit()
    else:
        player.nickname = nickname
        db.session.commit()
    SOCKET_PLAYER[sid] = {'email': email, 'nickname': nickname, 'player_id': player.id}
    rp = RoomPlayer(room_id=room_db.id, player_id=player.id, socket_id=sid, score=0)
    db.session.add(rp)
    db.session.commit()
    room_state = ROOMS_IN_MEMORY.get(room_id)
    if not room_state:
        room_state = {
            'id': room_id,
            'maxPlayers': room_db.max_players,
            'players': [],
            'status': 'waiting',
            'deck': None,
            'flipped': [],
            'scores': {},
            'currentTurnIndex': 0,
            'pairCount': 8
        }
        ROOMS_IN_MEMORY[room_id] = room_state
    room_state['players'].append({'id': sid, 'nickname': nickname, 'email': email, 'score': 0})
    room_state['scores'][sid] = 0
    join_room(room_id)
    emit('joinedRoom', {'roomId': room_id, 'room': room_state})
    emit('roomUpdate', room_state, room=room_id)

@socketio.on('startGame')
def on_start_game(data):
    sid = request.sid
    room_id = (data.get('roomId') or '').strip().upper()
    room_state = ROOMS_IN_MEMORY.get(room_id)
    if not room_state or room_state['status'] != 'waiting':
        emit('error', {'message': 'לא ניתן להתחיל משחק'})
        return
    if room_state['players'][0]['id'] != sid:
        emit('error', {'message': 'רק יוצר החדר יכול להתחיל'})
        return
    if len(room_state['players']) < room_state['maxPlayers']:
        emit('error', {'message': f"מחכים לעוד {room_state['maxPlayers'] - len(room_state['players'])} שחקן/ים. לא ניתן להתחיל עד שכל השחקנים הצטרפו."})
        return
    room_state['status'] = 'playing'
    room_state['deck'] = create_shuffled_deck(room_state['pairCount'])
    room_state['flipped'] = []
    room_state['currentTurnIndex'] = 0
    room_db = Room.query.filter_by(code=room_id).first()
    if room_db:
        room_db.status = 'playing'
        db.session.commit()
    emit('gameStarted', {'room': room_state, 'deck': room_state['deck']}, room=room_id)

def _delayed_no_match(room_id, card_a, card_b, next_idx, next_sid):
    time.sleep(2)
    room_state = ROOMS_IN_MEMORY.get(room_id)
    if room_state and room_state['status'] == 'playing':
        room_state['flipped'] = []
        room_state['currentTurnIndex'] = next_idx
        socketio.emit('noMatch', {
            'cardIndices': [card_a, card_b],
            'nextTurn': next_sid,
            'room': room_state
        }, room=room_id)


@socketio.on('flipCard')
def on_flip_card(data):
    sid = request.sid
    room_id = (data.get('roomId') or '').strip().upper()
    room_state = ROOMS_IN_MEMORY.get(room_id)
    if not room_state or room_state['status'] != 'playing' or not room_state.get('deck'):
        return
    current_sid = room_state['players'][room_state['currentTurnIndex']]['id']
    if sid != current_sid:
        emit('error', {'message': 'לא תורך'})
        return
    try:
        card_index = int(data.get('cardIndex', -1))
    except (TypeError, ValueError):
        emit('error', {'message': 'בחירת קלף לא תקינה'})
        return
    if card_index < 0 or card_index >= len(room_state['deck']):
        emit('error', {'message': 'בחירת קלף לא תקינה'})
        return
    card = room_state['deck'][card_index]
    if card_index in room_state['flipped'] or len(room_state['flipped']) >= 2:
        return
    room_state['flipped'].append(card_index)
    emit('cardFlipped', {'cardIndex': card_index, 'card': card, 'flipped': room_state['flipped']}, room=room_id)
    if len(room_state['flipped']) == 2:
        a, b = room_state['flipped'][0], room_state['flipped'][1]
        ca, cb = room_state['deck'][a], room_state['deck'][b]
        if ca['pairId'] == cb['pairId']:
            room_state['scores'][sid] = room_state['scores'].get(sid, 0) + 1
            for p in room_state['players']:
                if p['id'] == sid:
                    p['score'] = room_state['scores'][sid]
                    break
            category = ca['category']
            room_state['flipped'] = []
            next_idx = (room_state['currentTurnIndex'] + 1) % len(room_state['players'])
            next_sid = room_state['players'][next_idx]['id']
            room_state['currentTurnIndex'] = next_idx
            emit('match', {
                'cardIndices': [a, b],
                'category': category,
                'scores': room_state['scores'],
                'nextTurn': next_sid,
                'room': room_state
            }, room=room_id)
        else:
            next_idx = (room_state['currentTurnIndex'] + 1) % len(room_state['players'])
            next_sid = room_state['players'][next_idx]['id']
            socketio.start_background_task(
                _delayed_no_match, room_id, a, b, next_idx, next_sid
            )

@socketio.on('activityDone')
def on_activity_done(data):
    room_id = (data.get('roomId') or '').strip().upper()
    emit('activityClosed', room=room_id)

@socketio.on('disconnect')
def on_disconnect():
    sid = request.sid
    SOCKET_PLAYER.pop(sid, None)
    for code, room_state in list(ROOMS_IN_MEMORY.items()):
        if any(p['id'] == sid for p in room_state['players']):
            room_state['players'] = [p for p in room_state['players'] if p['id'] != sid]
            room_state['scores'].pop(sid, None)
            if len(room_state['players']) == 0:
                del ROOMS_IN_MEMORY[code]
                room_db = Room.query.filter_by(code=code).first()
                if room_db:
                    db.session.delete(room_db)
                    db.session.commit()
            else:
                room_state['currentTurnIndex'] = room_state['currentTurnIndex'] % len(room_state['players'])
                emit('roomUpdate', room_state, room=code)
            leave_room(code)
            break

if __name__ == '__main__':
    uri = app.config.get('SQLALCHEMY_DATABASE_URI') or ''
    if not uri or '@' not in uri:
        print('ERROR: Set DATABASE_URL in backend/.env with username and password.')
        print('Example: DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/ndfa_memory_game')
        exit(1)
    with app.app_context():
        db.create_all()
    socketio.run(app, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)
