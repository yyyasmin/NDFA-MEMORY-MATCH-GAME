from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Player(db.Model):
    __tablename__ = 'players'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    nickname = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {'id': self.id, 'email': self.email, 'nickname': self.nickname}


class Room(db.Model):
    __tablename__ = 'rooms'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False, index=True)
    max_players = db.Column(db.Integer, nullable=False, default=3)
    status = db.Column(db.String(20), default='waiting')  # waiting, playing, finished
    host_socket_id = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    room_players = db.relationship('RoomPlayer', backref='room', lazy='dynamic', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'code': self.code,
            'max_players': self.max_players,
            'status': self.status,
            'players': [rp.to_dict() for rp in self.room_players]
        }


class RoomPlayer(db.Model):
    __tablename__ = 'room_players'
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=False)
    player_id = db.Column(db.Integer, db.ForeignKey('players.id'), nullable=False)
    socket_id = db.Column(db.String(100), nullable=True)
    score = db.Column(db.Integer, default=0)
    player = db.relationship('Player', backref=db.backref('room_players', lazy=True))

    def to_dict(self):
        return {
            'id': self.player_id,
            'socket_id': self.socket_id,
            'nickname': self.player.nickname if self.player else None,
            'email': self.player.email if self.player else None,
            'score': self.score
        }
