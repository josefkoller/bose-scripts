import getpass
import sys
import telnetlib
import sqlite3
from datetime import datetime
import ConfigParser
from subprocess import call, Popen, PIPE
from time import sleep
import traceback
import logging

config = ConfigParser.ConfigParser()
config.readfp(open('config.cfg'))

logging_format = '%(asctime)s %(message)s'
logging.basicConfig(filename=config.get('system', 'log_file'), \
  level=logging.DEBUG, format=logging_format)
console = logging.StreamHandler()
console.setLevel(logging.INFO)
console.setFormatter(logging.Formatter(logging_format))
logging.getLogger('').addHandler(console)

def log(message):
  logging.info(message)

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
  database_connection.text_factory = str
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

def getCurrentTrackInfo():
  send('ext info')
  text = expect('OK')
  track_artist = extractTrackInfo(text, 'Track Artist')
  track_album = extractTrackInfo(text, 'Track Album')
  track_name = extractTrackInfo(text, 'Track Name')
  return (track_artist, track_album, track_name)

def getCurrentTrack():
  (track_artist, track_album, track_name) = getCurrentTrackInfo()
  return getTrackPath(track_artist, track_album, track_name)

def addCurrentTrackToPlaylist(playlist_file):
  track_path = getCurrentTrack()
  if track_path == None:
    return
  stream = open(playlist_file, 'r+')
  contents = stream.read()
  if contents.find(track_path) > -1:
    log('the playlist %s already contains %s' % (playlist_file, track_path))
    return
  stream.write('\n' + track_path)
  log('added %s to playlist %s' % (track_path, playlist_file))

def executeShellCommand(command):
  log(command)
  call(command)

def executeShellCommandAndReturnStdOutput(command):
  log(command)
  process = Popen(command, stdin=PIPE, stdout=PIPE)
  (output, error) = process.communicate()
  log('output')
  log(output)
  if error:
    log(error)
    return
  return output.strip()

def stream(music_file):
  pressKey('stop')

  transcoder = config.get('transcode', 'binary')
  output_file = config.get('transcode', 'output_file')
  command = [transcoder, '-i', "%s" % music_file, '-y', \
          '-metadata', 'album="PC"', '-qscale:a', '2',  output_file]
  executeShellCommandAndReturnStdOutput(command)

  pressKey('preset_%d' % config.getint('presets', 'stream'))
  waitForPlaying()

def isPlaying():
  send('ext status')
  text = expect('OK')
  return text.find('Playing') > -1

def waitForPlaying():
  begin = datetime.now()
  is_playing = False
  while not is_playing:
    duration_seconds = (datetime.now() - begin).seconds
    if duration_seconds > config.getint('system', 'wait_for_playing_timeout'):
      raise Exception('waited %d for playing state' % duration_seconds)
    is_playing = isPlaying()
    log('is playing %s after %d seconds' % (str(is_playing), duration_seconds))

def speakTextAndWait(text):
  converter = config.get('speak', 'binary')
  output_file = config.get('speak', 'output_file')
  executeShellCommand([converter, '--lang', 'en-GB', '--wave', output_file, text])
  speak_duration= float(executeShellCommandAndReturnStdOutput(['soxi', '-D', output_file]))
  sleep_duration = speak_duration + config.getint('speak', 'additional_timeout_seconds')

  setRepeat('off')
  stream(output_file)

  log('waiting %f seconds' % sleep_duration)
  sleep(sleep_duration)
  setRepeat('on')

def speakCurrentTrackInfo():
  (track_artist, track_album, track_name) = getCurrentTrackInfo()
  text = '"%s, %s"' % (track_artist, track_name)
  speakTextAndWait(text)
  pressKey('preset_%d' % config.getint('presets', 'all_music'))

def likeCurrentTrack():
  playlist_file = config.get('playlists', 'root') + config.get('playlists', 'like_file')
  addCurrentTrackToPlaylist(playlist_file)

def dislikeCurrentTrack():
  playlist_file = config.get('playlists', 'root') + config.get('playlists', 'dislike_file')
  addCurrentTrackToPlaylist(playlist_file)

def getVolume():
  send('sys volume')
  text = expect('OK')
  start_text = 'target = '
  start = text.find(start_text) + len(start_text)
  end = text.find(' actual')
  return int(text[start:end])

def setVolume(option): # value | mute: 'toogle', 'on', 'off'
  send('sys volume ' + option)
  expect('OK')

def setRepeat(option): # 'on', 'off', 'one'
  send('ext repeat ' + option)
  expect('OK')

def pressKey(key):
  send('key ' + key)
  expect('OK')

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
    try:
        if text.find(LIKE_PATTERN) > -1:
            likeCurrentTrack()
            speakCurrentTrackInfo()
        elif text.find(DISLIKE_PATTERN) > -1:
            dislikeCurrentTrack()
            speakCurrentTrackInfo()
            waitForPlaying()
            pressKey('next')
    except:
        text = traceback.format_exc()
        log(text)
