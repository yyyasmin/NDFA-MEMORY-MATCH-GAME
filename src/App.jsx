import React, { useState, useEffect, useCallback } from 'react'
import { io } from 'socket.io-client'
import { getRandomActivity, getCardEmoji } from './activities'

// Backend URL: choose via .env.local (local dev) or Netlify env (production).
const RENDER_BACKEND = 'https://ndfa-memory-match-game.onrender.com'
const LOCAL_BACKEND = 'http://localhost:5000'
function getBackendUrl() {
  if (import.meta.env.VITE_BACKEND_URL) return import.meta.env.VITE_BACKEND_URL
  if (typeof window !== 'undefined' && window.location.hostname === 'ndfa-memory-match-game.netlify.app') return RENDER_BACKEND
  if (import.meta.env.VITE_USE_RENDER_BACKEND === 'true' || import.meta.env.VITE_USE_RENDER_BACKEND === '1') return RENDER_BACKEND
  return LOCAL_BACKEND
}
const API_BASE = getBackendUrl()
const SOCKET_URL = getBackendUrl()
const BACKEND_DISPLAY = API_BASE

function App() {
  const [screen, setScreen] = useState('login')
  const [email, setEmail] = useState('')
  const [nickname, setNickname] = useState('')
  const [socket, setSocket] = useState(null)
  const [error, setError] = useState('')
  const [roomsList, setRoomsList] = useState([])
  const [roomId, setRoomId] = useState('')
  const [room, setRoom] = useState(null)
  const [deck, setDeck] = useState([])
  const [flipped, setFlipped] = useState([])
  const [matched, setMatched] = useState([])
  const [activityModal, setActivityModal] = useState(null)
  const [maxPlayers, setMaxPlayers] = useState(2)
  const [joinRoomCode, setJoinRoomCode] = useState('')

  const connectSocket = useCallback((loginEmail, loginNickname) => {
    const em = (loginEmail != null ? loginEmail : email).toString().trim()
    const nick = (loginNickname != null ? loginNickname : nickname).toString().trim()
    const isRender = SOCKET_URL && SOCKET_URL.includes('onrender.com')
    let currentSocket = null
    let retryTimeoutId = null

    function tryConnect(retryCount) {
      if (currentSocket) {
        currentSocket.removeAllListeners()
        currentSocket.disconnect()
        currentSocket = null
      }
      const s = io(SOCKET_URL || window.location.origin, {
        path: '/socket.io',
        transports: isRender ? ['polling'] : ['polling', 'websocket']
      })
      currentSocket = s

      s.on('connect', () => {
        setError('')
        setSocket(s)
        s.emit('register', { email: em, nickname: nick })
      })
      s.on('connect_error', () => {
        s.disconnect()
        if (isRender && retryCount < 5) {
          setError(`מעיר את השרת... נסיון ${retryCount + 1}/5 (חכה עד 30 שניות)`)
          retryTimeoutId = setTimeout(() => tryConnect(retryCount + 1), 6000)
        } else {
          setError('לא ניתן להתחבר. הער את השרת: פתח בחלון חדש ' + (SOCKET_URL || '') + '/api/health חכה ל־{"status":"ok"} ולחץ שוב התחבר והמשך.')
        }
      })
      s.on('disconnect', (reason) => {
        if (reason === 'io server disconnect' || reason === 'io client disconnect') return
        setError('התנתקת מהשרת. נסה להתחבר שוב.')
      })
      s.on('registered', () => setScreen('lobby'))
      s.on('error', (data) => setError(data?.message || 'שגיאה'))
      s.on('roomCreated', (data) => {
        setRoomId(data.roomId)
        setRoom(data.room)
        setScreen('room')
        setError('')
      })
      s.on('joinedRoom', (data) => {
        setRoomId(data.roomId)
        setRoom(data.room)
        setScreen('room')
        setError('')
      })
      s.on('roomUpdate', (data) => setRoom(data))
      s.on('roomsList', (data) => setRoomsList(data || []))
      s.on('gameStarted', (data) => {
        setRoom(data.room)
        setDeck(data.deck || [])
        setFlipped([])
        setMatched([])
        setScreen('game')
        setError('')
      })
      s.on('cardFlipped', (data) => setFlipped(data.flipped || []))
      s.on('match', (data) => {
        setMatched((m) => [...m, ...(data.cardIndices || [])])
        setFlipped([])
        if (data.room) setRoom(data.room)
        const act = getRandomActivity(data.category)
        setActivityModal({ ...act, category: data.category })
      })
      s.on('noMatch', (data) => {
        setFlipped([])
        if (data.room) setRoom(data.room)
      })
      s.on('activityClosed', () => setActivityModal(null))
    }

    tryConnect(0)
    return () => {
      if (retryTimeoutId) clearTimeout(retryTimeoutId)
      if (currentSocket) {
        currentSocket.removeAllListeners()
        currentSocket.disconnect()
      }
    }
  }, [email, nickname])

  useEffect(() => {
    if (screen === 'lobby' && socket) socket.emit('listRooms')
    const id = setInterval(() => {
      if (screen === 'lobby' && socket) socket.emit('listRooms')
    }, 3000)
    return () => clearInterval(id)
  }, [screen, socket])

  const handleLogin = async (e) => {
    e.preventDefault()
    setError('')
    const em = email.trim()
    const nick = nickname.trim()
    if (!em || !nick) {
      setError('אימייל ושם חובה')
      return
    }
    setEmail(em)
    setNickname(nick)

    // If backend is Render (free tier), wake it first so the socket can connect.
    if (SOCKET_URL && SOCKET_URL.includes('onrender.com')) {
      setError('מעיר את השרת...')
      try {
        const ctrl = new AbortController()
        const t = setTimeout(() => ctrl.abort(), 60000)
        await fetch(`${SOCKET_URL}/api/health`, { signal: ctrl.signal })
        clearTimeout(t)
      } catch (_) {
        // Timeout or network error – continue anyway, retries will run
      }
      setError('')
    }

    connectSocket(em, nick)
  }

  const handleCreateRoom = () => {
    setError('')
    if (!socket) return
    socket.emit('createRoom', { maxPlayers: maxPlayers, email, nickname })
  }

  const handleJoinRoom = (code) => {
    setError('')
    if (!socket || !code) return
    socket.emit('joinRoom', { roomId: code.trim().toUpperCase(), email, nickname })
  }

  const handleStartGame = () => {
    if (!socket) return
    socket.emit('startGame', { roomId })
  }

  const handleFlip = (cardIndex) => {
    if (!socket || !room || room.status !== 'playing') return
    if (flipped.length >= 2 || flipped.includes(cardIndex) || matched.includes(cardIndex)) return
    const currentId = room.players[room.currentTurnIndex]?.id
    if (socket.id !== currentId) return
    socket.emit('flipCard', { roomId, cardIndex })
  }

  const closeActivity = () => {
    if (socket) socket.emit('activityDone', { roomId })
    setActivityModal(null)
  }

  const currentTurnId = room?.players?.[room?.currentTurnIndex]?.id
  const isMyTurn = socket && currentTurnId === socket.id

  return (
    <div className="app">
      <h1>משחק זיכרון NDFA</h1>

      {screen === 'login' && (
        <form onSubmit={handleLogin}>
          <div className="form-row">
            <label>אימייל</label>
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="your@email.com" />
          </div>
          <div className="form-row">
            <label>שם במשחק</label>
            <input type="text" value={nickname} onChange={(e) => setNickname(e.target.value)} placeholder="השם שלי" />
          </div>
          {error && <p className="error-msg">{error}</p>}
          <button type="submit">התחבר והמשך</button>
        </form>
      )}

      {screen === 'lobby' && (
        <>
          <p>שלום, {nickname}. בחר ליצור חדר או להצטרף לחדר קיים.</p>
          <div className="lobby-actions">
            <label>מספר שחקנים: </label>
            <select value={maxPlayers} onChange={(e) => setMaxPlayers(Number(e.target.value))}>
              <option value={1}>1</option>
              <option value={2}>2</option>
              <option value={3}>3</option>
            </select>
            <button onClick={handleCreateRoom}>צור חדר חדש</button>
          </div>
          <h3>חדרים פתוחים</h3>
          <ul className="room-list">
            {roomsList.length === 0 && <li>אין חדרים פתוחים. צור חדר חדש.</li>}
            {roomsList.map((r) => (
              <li key={r.roomId || r.code}>
                <span>חדר {r.roomId || r.code} – {r.players?.map((p) => p.nickname).join(', ')} ({r.players?.length}/{r.maxPlayers})</span>
                <button className="join-btn" onClick={() => handleJoinRoom(r.roomId || r.code)}>הצטרף</button>
              </li>
            ))}
          </ul>
          <div className="form-row">
            <label>הזן קוד חדר להצטרפות</label>
            <input value={joinRoomCode} onChange={(e) => setJoinRoomCode(e.target.value)} placeholder="קוד חדר" />
            <button onClick={() => handleJoinRoom(joinRoomCode)}>הצטרף לחדר</button>
          </div>
          {error && <p className="error-msg">{error}</p>}
        </>
      )}

      {screen === 'room' && room && (
        <>
          <p className="room-code">קוד החדר: <strong>{roomId}</strong></p>
          <p>שחקנים בחדר: {room.players?.map((p) => p.nickname).join(', ')} ({room.players?.length}/{room.maxPlayers})</p>
          {room.players?.[0]?.id === socket?.id && room.players?.length === room.maxPlayers && (
            <button onClick={handleStartGame}>התחל משחק</button>
          )}
          {room.players?.[0]?.id === socket?.id && room.players?.length < room.maxPlayers && (
            <p>מחכים לעוד {room.maxPlayers - room.players?.length} שחקן/ים להצטרף לפני שמתחילים.</p>
          )}
          {room.players?.[0]?.id !== socket?.id && <p>מחכים לבעל החדר שיתחיל...</p>}
          {error && <p className="error-msg">{error}</p>}
        </>
      )}

      {screen === 'game' && room && (
        <>
          <p className="player-identity">אתה משחק כ: <strong>{nickname}</strong></p>
          <div className="scores">
            {room.players?.map((p) => (
              <span key={p.id} className={p.id === socket?.id ? 'score-you' : ''}>
                {p.nickname}: {room.scores?.[p.id] ?? 0}
                {p.id === currentTurnId && ' ← תור'}
              </span>
            ))}
          </div>
          <p className="turn-indicator">{isMyTurn ? 'עכשיו תורך!' : 'תור של שחקן אחר'}</p>
          <div className="game-board">
            {deck.map((card, i) => (
              <div
                key={i}
                className={`card ${flipped.includes(i) || matched.includes(i) ? 'flipped' : ''} ${matched.includes(i) ? 'matched' : ''}`}
                onClick={() => handleFlip(i)}
              >
                <div className="card-inner">
                  <div className="card-face card-back">?</div>
                  <div className="card-face card-front">{getCardEmoji(card.category)}</div>
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      {activityModal && (
        <div className="modal-overlay">
          <div className="modal">
            <h2>{activityModal.emoji} {activityModal.title}</h2>
            <p className="activity-text">{activityModal.text}</p>
            <button className="done-btn" onClick={closeActivity}>סיימתי את הפעילות</button>
          </div>
        </div>
      )}

      <p className="backend-indicator" title="Which backend this frontend connects to">
        Backend: <span style={{ userSelect: 'all', wordBreak: 'break-all' }}>{BACKEND_DISPLAY}</span>
      </p>
    </div>
  )
}

export default App
