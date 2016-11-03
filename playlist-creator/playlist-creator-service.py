import getpass
import sys
import telnetlib
import sqlite3
from time import gmtime, strftime
import ConfigParser

config = ConfigParser.ConfigParser()
config.readfp(open('config.cfg'))

LIKE_PLAYLIST_FILE = config.get('playlists', 'root') + config.get('playlists', 'like_file')
DISLIKE_PLAYLIST_FILE = config.get('playlists', 'root') + config.get('playlists', 'dislike_file')
LOG_FILE = config.get('system', 'log_file')

print 'log: ' + LOG_FILE
log_stream = open(LOG_FILE, 'a+')


def log(message):
  if message == None:
    message = 'None'
  message = strftime("%Y-%m-%d %H:%M:%S", gmtime()) + ' ' + message
  log_stream.write('\n' + message)
  log_stream.flush()
  print message

def expect(message):
  result = connection.expect([message], config.getint('telnet', 'timeout_seconds'))
  index = result[0]
  text = result[2]
  if index > -1:
    log('success: ' + text)
    return text
  else:
    log('failed, read: ' + text)
    return ''

def send(message):
  log('sending...')
  message += '\n'
  log(message)
  connection.write(message)

def extractTrackInfo(text, title):
  title += ':'
  start = text.find(title) + len(title)
  end = text.find('\n', start)
  return text[start:end].strip()

def getTrackPath(track_artist, track_album, track_name):
  log('searching: ')
  log('Artist: ' + track_artist)
  log('Album: ' + track_album)
  log('Track: ' + track_name)
  database_connection = sqlite3.connect(config.get('database', 'path'))
  cursor = database_connection.cursor()
  data = (track_artist, track_album, track_name)
  statement = 'select PATH from details where artist=? and album=? and title=?'
  cursor.execute(statement, data)
  path = cursor.fetchone()
  if path:
      path = path[0].strip()
  log('database result: ')
  log(path)
  return path

def getCurrentTrack():
  send('ext info')
  text = expect('OK')
  track_artist = extractTrackInfo(text, 'Track Artist')
  track_album = extractTrackInfo(text, 'Track Album')
  track_name = extractTrackInfo(text, 'Track Name')
  return getTrackPath(track_artist, track_album, track_name)

def addCurrentTrackToPlaylist(playlist_file):
  track_path = getCurrentTrack()
  if track_path == None:
    return
  stream = open(playlist_file, 'r+')
  contents = stream.read()
  log('contents: ' + contents)
  log('track: ' + track_path)
  if contents.find(track_path) > -1:
    log('the playlist %s already contains %s' % (playlist_file, track_path))
    return
  stream.write('\n' + track_path)
  log('added %s to playlist %s' % (track_path, playlist_file))

def likeCurrentTrack():
  addCurrentTrackToPlaylist(LIKE_PLAYLIST_FILE)

def dislikeCurrentTrack():
  addCurrentTrackToPlaylist(DISLIKE_PLAYLIST_FILE)

log('connecting to telnet server')
connection = telnetlib.Telnet(config.get('telnet', 'host'), config.get('telnet', 'port'))
expect('->')
send('ir echo on')
expect('OK')
send('async_responses on')
expect('Done')

LIKE_PATTERN = 'Key()=5, State()=1'
DISLIKE_PATTERN = 'Key()=6, State()=1'
log('starting to watch the ir keys')
while True:
    text = connection.read_until('->')
    log(text)
    if text.find(LIKE_PATTERN) > -1:
        likeCurrentTrack()
    if text.find(DISLIKE_PATTERN) > -1:
        dislikeCurrentTrack()

