#!/usr/bin/env python
import re
import json
import requests
import time
import sys
from urllib import parse
from datetime import datetime, timedelta
import threading

url = "https://textyserver.appspot.com/"
headers = {
  "origin" : "https://mightytext.net",
  "accept-enoding" : "gzip, deflate",
  "accept-language" : "en-US,en;q=0.8",
  "user-agent" : "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/43.0.2357.125 Safari/537.36",
  "content-type" : "application/x-www-form-urlencoded; charset=UTF-8",
  "accept" : "application/json, text/javascript, */*; q=0.01",
  "referer" : "https://mightytext.net/web8/?exp=1",
  "authority" : "textyserver.appspot.com",
  "Content-Length" : "0"}
headers['cookie'] = open('cookie').read()
selfnum = '6143903969'
# clean = lambda n: re.sub('(^\+|[^0-9]|\|)','', re.sub('\^+1','',n))
clean = lambda n: re.sub('[^0-9\|]','', re.sub('(\+1|1 )','',n))
namer = lambda n: n.split()[0]
messages = []
contactss = []
sending = False
updated = True
mlock = threading.Lock()

def update_messages():
  global messages
  try:
    r = json.loads(requests.get(url=url+'api', headers=headers, params={'function':'GetMessages', 'start_range':0,'end_range':100}).text)
    if 'user' in r: return messages
  except: return []
  
  with mlock:
    try:
        seen = [m['id'] for m in messages] if messages else []
        new = [m for m in r['messages'] if m['id'] not in seen]
        new.reverse()
        new = [{'body'  : parse.unquote_plus(m['body']),
                'id'    : m['id'],
                'time'  : (datetime.strptime(m['ts_carrier'], "%b %d, %Y %I:%M:%S %p") - timedelta(hours=4)) \
                            .strftime("%m/%d/%y %I:%M:%S").split(),
                'phone' : clean(m['phone_num']),
                'read'  : m['is_read'],
                'sent'  : (m['inbox_outbox'] == 61),
                } for m in new]
        messages.extend(new)
        with open('messages', 'w') as f: f.write(json.dumps(messages))
        return new
    except:
        print(r)
        return []

def get_contacts():
  try:
    r = json.loads(requests.get(url=url+'phonecontact', headers=headers, params={'function':'getPhoneContacts'}).text)
  except: return {}
  print('\n'.join([c['phoneList'][0]['phoneNumber'] for c in r]))
  contacts = {clean(c['phoneList'][0]['phoneNumber']):c['displayName'] for c in r}
  with open('contacts', 'w') as f: f.write(json.dumps(contacts))
  return contacts

def send(text, number):
    print(number)
    res = (requests.post(url=url+'client', headers=headers, 
      data={'function':'send', 'deviceType':'ac2dm', 'source_client':'31', 'type':10, 'deviceType':'ac2dm','action':'send_sms',
        'action_data' : text,
        'phone'       : number,
        }))
    return res.status_code

def say(m):
  global contacts
  old = datetime.now() - datetime.strptime(' '.join(m['time']), "%m/%d/%y %I:%M:%S") > timedelta(1)
  name = ', '.join([namer(contacts[p]) if p in contacts else p for p in m['phone'].split('|')])
  print('[\033[{}m{}\033[0m] [\033[{}m{}\033[0m] {}'.format(
    '91' if m['sent'] else '95',
    m['time'][0] if old else m['time'][1], 
    #90 + (sum([ord(c) for c in name])%7),
    '90',
    name,
    #contacts[m['phone']] if len(m['phone']) == 10 else ', '.join(contacts[p] for p in m['phone'].split('|')),
    m['body']))

# threads
def sender(recp=None):
  global messages
  global contacts
  global sending
  global mlock
  rcontacts = {v: k for k, v in contacts.items()}
  with mlock:
    ms = [m for m in messages if ((m['phone'] == rcontacts[recp]) if recp else True)][-25:]
    for m in ms: say(m)

  while 1:
    print('[\033[{}m{}\033[0m] '.format('96', recp if recp else "--------"), end="")
    tosend = input()
    if tosend.startswith('\\'):
      recp = tosend[1:] if tosend[1:] in rcontacts else recp
    else:
      if len(tosend.strip()) > 0:
        res = send(tosend, rcontacts[recp])
        if res is not 200:
          print('[\033[{}m{}\033[0m]\n{}'.format(91, 'ERROR', 'STAUTS CODE: {}'.format(res)))
        else: print('good')
          
    with mlock:
      sending = True

def updater():
  global messages
  global sending
  global mlock
  while 1: 
    delay = 5
    new = update_messages()
    if new:
      print()
      for m in new: say(m)
      print('\r[\033[{}m{}\033[0m] {}\r'.format('93', "UPDATED", 'Loaded {} New Messages'.format(len(new))), end="")
      with mlock:
        sending = False
    
    with mlock:
      if sending: delay = 1
    
    time.sleep(delay)

if __name__ == '__main__':
  with open('contacts') as f: contacts = json.loads(f.read())
  if len(contacts) == 0: contacts = get_contacts()
  with open('messages') as f: messages = json.loads(f.read())
  with open('/home/sachin/drive/people', 'w') as f: f.write('\n'.join(contacts.values()))
  person = ' '.join(sys.argv[1:])
  thread = threading.Thread(target=updater)
  thread.daemon = True
  thread.start()
  sender(person if person in contacts.values() else None)
