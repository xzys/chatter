#!/usr/bin/env python
import re
import json
import requests
import time
import sys
from urllib import parse
from datetime import datetime, timedelta
import threading
import subprocess
import os

abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)
root = '/home/sachin/drive/projects/chatter/'

url = "https://textyserver.appspot.com/"
headers={
        "accept": "*/*",
        "accept-encoding": "gzip, deflate",
        "accept-language": "en-US,en;q=0.8",
        "authority": "textyserver.appspot.com",
        "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
        "origin": "https://mightytext.net",
        "referer": "https://mightytext.net/web8/?exp=1",
        "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/43.0.2357.125 Safari/537.36",
        "Content-Length" : "0"}
    
headers['cookie'] = open(root+'cookie').read()
selfnum = '6143903969'
# clean = lambda n: re.sub('(^\+|[^0-9]|\|)','', re.sub('\^+1','',n))
clean = lambda n: re.sub('[^0-9\|]','', re.sub('(\+1|1 )','',n))
namer = lambda n: n.split()[0]
messages = []
contactss = []
sending = False
updated = True
recp = None
tosend = ''
mlock = threading.Lock()

def update_messages():
  global messages
  try:
    r = json.loads(requests.get(url=url+'api', headers=headers, params={'function':'GetMessages', 'start_range':0,'end_range':100}).text)
    #print(r['messages'][0])
    if 'user' in r: return messages
  except: return []
  
  with mlock:
    try:
        seen = [m['id'] for m in messages] if messages else []
        new = [m for m in r['messages'] if m['id'] not in seen]
        new.reverse()
        new = [{'body'  : parse.unquote_plus(m['body']),
                'id'    : m['id'],
                'time'  : (datetime.strptime(m['ts_server'], "%b %d, %Y %I:%M:%S %p") - timedelta(hours=4)) \
                            .strftime("%m/%d/%y %I:%M:%S").split(),
                'phone' : clean(m['phone_num']),
                'clean' : m['phone_num_clean'],
                'read'  : m['is_read'],
                'sent'  : (m['inbox_outbox'] == 61),
                } for m in new]
        messages.extend(new)
        with open(root+'messages', 'w') as f: f.write(json.dumps(messages))
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
  with open(root+'contacts', 'w') as f: f.write(json.dumps(contacts))
  return contacts

def send(text, number):
    # res = (requests.post(url=url+'client?function=send&deviceType=ac2dm&source_client=31', headers=headers, 
    #   data={
    #       'function':'send', 'deviceType':'ac2dm', 'source_client':'31', 
    #       'type':10, 'deviceType':'ac2dm','action':'send_sms',
    #     'action_data' : text,
    #     'phone'       : ,
    #     })
    # res =  subprocess.check_output([root+'send.sh', \
    #        parse.quote_plus('({}) {}-{}'.format(number[:3], number[3:6], number[6:])), 
    #        parse.quote_plus(text)], shell=True)
    res = subprocess.check_output(['/bin/sh', root+'/send.sh', 
                    parse.quote_plus('+1({}) {}-{}'.format(number[:3], number[3:6], number[6:])), 
                    # parse.quote_plus('+({}) {}-{}'.format(number[:3], number[3:6], number[6:])), 
                    parse.quote_plus(text)])
    return 200

linelen = 0
def say(m):
  global contacts
  global linelen
  old = datetime.now() - datetime.strptime(' '.join(m['time']), "%m/%d/%y %H:%M:%S") > timedelta(1)
  name = ', '.join([namer(contacts[p]) if p in contacts else p for p in m['phone'].split('|')])
  linelen = max(linelen, len(name))
  s = '\033[{}m{} \033[{}m{}\033[93m'.format(
    90,
    m['time'][0] if old else m['time'][1], 
   '91' if m['sent'] else '95',
    name,
    )
  print(s.ljust(40) + '| \033[0m' + m['body'])
#  print('[\033[{}m{}\033[0m] [\033[{}m{}\033[0m] {}'.format(
    #'90',
 #   '91' if m['sent'] else '95',
    #90 + (sum([ord(c) for c in name])%7),
  #  90,
    #contacts[m['phone']] if len(m['phone']) == 10 else ', '.join(contacts[p] for p in m['phone'].split('|')),

# threads
def sender():
  global messages
  global contacts
  global sending
  global mlock
  global updated
  global tosend
  global recp 
  rcontacts = {v: k for k, v in contacts.items()}
  with mlock:
    ms = [m for m in messages if ((m['phone'] == rcontacts[recp]) if recp else True)][:]
    for m in ms: say(m)
  while 1:
    print('[\033[{}m{}\033[0m] '.format('96', recp if recp else "--------"), end="")
    tosend = input()
    with mlock:
      if tosend.startswith('\\'):
        r = [r for r in rcontacts.keys() if r.startswith(tosend[1:])]
        recp = r[0] if len(r) > 0 else recp
      elif recp and '\\' not in tosend and not updated:
        if len(tosend.strip()) > 0:
          sending = True
          res = send(tosend, rcontacts[recp])
          if res is not 200:
            print('[\033[{}m{}\033[0m]\n{}'.format(91, 'ERROR', 'STAUTS CODE: {}'.format(res)))
          else: pass
      updated = False
          

def updater():
  global messages
  global sending
  global mlock
  global tosend
  global updated
  global recp
  while 1: 
    delay = 5
    new = update_messages()
    if new:
      print('')
      for m in new: 
        if tosend == m['body'] and m['sent']: print('\033[A\033[A',end='')
        else: print('\033[A',end='')
        say(m)
      print('\r[\033[{}m{}\033[0m] {}\r'.format('93', "UPDATED", '{} New Messages'.format(len(new))), end="")
      # print('\r[\033[{}m{}\033[0m] {}'.format('93', "UPDATED", '{}'.format(len(new))))
      with mlock:
        sending = False
        updated = True
    
    with mlock:
      if sending: delay = 1
    
    time.sleep(delay)

if __name__ == '__main__':
  with open(root+'contacts') as f: contacts = json.loads(f.read())
  if len(contacts) == 0: contacts = get_contacts()
  with open(root+'messages') as f: messages = json.loads(f.read())
  with open('/home/sachin/drive/notes/people', 'w') as f: f.write('\n'.join(contacts.values()))
  thread = threading.Thread(target=updater)
  thread.daemon = True
  thread.start()
  r = [r for r in contacts.values() if r.split(' ')[0] == ' '.join(sys.argv[1:])]
  recp = r[1] if r else None
  sender()
