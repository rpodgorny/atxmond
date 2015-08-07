#!/usr/bin/python3

'''
atxmond.

Usage:
  atxmond

Options:
'''

__version__ = '0.0'

import sys
import flask
import json
import datetime
import threading
import subprocess
import logging
import time
import os
import re
import json
import pymongo
import docopt


HISTORY_LEN = 10
GEN_PNG = False

# TODO: globals are shit
app = flask.Flask(__name__)
db = pymongo.MongoClient().atxmon
data = []
evts = []  # TODO: this is shitty name
last_vals = {}  # TODO: shitty name

# TODO: move this
db.data.ensure_index('k')
db.data.ensure_index('t')
#db.data.ensure_index(['k', 'v'])
#db.data.ensure_index(['k', 't'])
#db.data.ensure_index(['k', 'v', 't'])
db.changes.ensure_index('k')
db.changes.ensure_index('t')


# TODO: ugly name, ugly functionality
def normalize(s):
	return s.replace('/', '__').replace(' ', '_').replace(':', '_')
#enddef

def load_json(fn):
	with open(fn, 'r') as f:
		return json.load(f)
	#endwith
#enddef

def save_json(data, fn):
	with open(fn, 'w') as f:
		return json.dump(data, f, indent=2)
	#endwith
#enddef

def load_alerts(fn):
	ret = []
	with open(fn, 'r') as f:
		for line in f:
			line = line.strip()
			if not line: continue

			reg_exp, operator, value = line.split(' ')
			value = int(value)

			ret.append((reg_exp, operator, value))
		#endfor
	#endwith
	return ret
#enddef

def load_events(fn):
	ret = []
	with open(fn, 'r') as f:
		for line in f:
			line = line.strip()
			if not line: continue

			reg_exp, operator, value = line.split(' ')
			value = int(value)

			ret.append((reg_exp, operator, value))
		#endfor
	#endwith
	return ret
#enddef

@app.route('/')
def index():
	return 'index'
#enddef

@app.route('/save', methods=['GET', 'POST'])
def save_many():
	d = flask.request.get_json(force=True)
	print('will save %s entries' % len(d))

	data.extend(d)

	return 'ok'
#enddef

@app.route('/show')
def show():
	x = []
	# TODO: find the actual query to find unique shit
	for k in db.data.unique(k).sort([('k', 1), ]):
		doc = db.data.find_one({'k': k})  # TODO: find the last one
		v = doc['v']
		t = doc['t']
		x.append((k, v, t))
	#endfor

	return flask.render_template('show.html', data_last=x)
#enddef

@app.route('/alerts')
def alerts():
	alerts = load_alerts('alerts.conf')

	x = []
	for reg_exp, operator, value in alerts:
		for k in sorted(last_vals.keys()):
			if not re.match(reg_exp, k): continue

			v, t = last_vals[k]

			if operator == '==':
				if v != value: continue
			elif operator == '!=':
				if v == value: continue
			else:
				raise Exception('unknown operator %s' % operator)
			#endif

			t = datetime.datetime.fromtimestamp(t).strftime('%Y-%m-%d %H:%M:%S')
			x.append((k, v, t))
		#endfor
	#endfor

	return flask.render_template('alerts.html', data_last=x)
#enddef

@app.route('/events')
def events():
	x = []
	for k, v, t in evts:
		t = datetime.datetime.fromtimestamp(t).strftime('%Y-%m-%d %H:%M:%S')
		x.append((k, v, t))
	#endfor

	return flask.render_template('events.html', data_last=x)
#enddef

@app.route('/show_last/<path:test>')
def show_last(test):
	x = []
	# TODO: actually show the last HISTORY_LEN ones
	for doc in db.data.find({'k': test}).sort([('t', 1), ]).limit(HISTORY_LEN):
		v = doc['v']
		t = doc['t']
		x.append((v, t))
	#endfor

	return flask.render_template('show_last.html', data_last=x)
#enddef

class MyThread(threading.Thread):
	def __init__(self):
		threading.Thread.__init__(self, daemon=False)

		self._run = True
	#enddef

	def run(self):
		logging.info('thread run')

		events = load_events('events.conf')

		while self._run:
			while data:
				i = data.pop(0)
				k = i['path']
				v = i['value']
				t = i['time']
				interval = i['interval']
				print('data', k, v, t, interval)

				db.data.insert_one({'k': k, 'v': v, 't': datetime.datetime.fromtimestamp(t)})

				if v != last_vals.get(k):
					print('change', k, v, t, interval)
					db.changes.insert_one({'k': k, 'v': v, 't': datetime.datetime.fromtimestamp(t)})

					for reg_exp, operator, value in events:
						if not re.match(reg_exp, k): continue

						if operator == '==':
							if v != value: continue
						elif operator == '!=':
							if v == value: continue
						else:
							raise Exception('unknown operator %s' % operator)
						#endif

						print('new event: %s %s' % (k, v))
						evts.append((k, v, t))
					#endfor
				#endif

				fn = normalize(k)

				if not os.path.isfile('rrd/%s.rrd' % fn):
					cmd = 'rrdtool create rrd/%s.rrd --start 0 --step %d DS:xxx:GAUGE:%d:U:U' % (fn, interval, interval * 2)
					cmd += ' RRA:AVERAGE:0.999:1:100 RRA:AVERAGE:0.999:100:100'
					print(cmd)
					subprocess.check_call(cmd, shell=True)
				#endif

				#cmd = 'rrdtool update rrd/%s.rrd %d:%s' % (fn, int(t - 1), v)
				#print(cmd)
				#subprocess.check_call(cmd, shell=True)

				cmd = 'rrdtool update rrd/%s.rrd %d:%s' % (fn, int(t), v)
				print(cmd)
				subprocess.check_call(cmd, shell=True)

				if GEN_PNG:
					cmd = 'rrdtool graph png/%s__10min.png --end now --start end-10m --units-exponent 0 DEF:xxx=rrd/%s.rrd:xxx:AVERAGE LINE2:xxx#FF0000' % (fn, fn, )
					print(cmd)
					subprocess.check_call(cmd, shell=True)

					cmd = 'rrdtool graph png/%s__1h.png --end now --start end-1h --units-exponent 0 DEF:xxx=rrd/%s.rrd:xxx:AVERAGE LINE2:xxx#FF0000' % (fn, fn, )
					print(cmd)
					subprocess.check_call(cmd, shell=True)

					cmd = 'rrdtool graph png/%s__1d.png --end now --start end-1d --units-exponent 0 DEF:xxx=rrd/%s.rrd:xxx:AVERAGE LINE2:xxx#FF0000' % (fn, fn, )
					print(cmd)
					subprocess.check_call(cmd, shell=True)

					cmd = 'rrdtool graph png/%s__1w.png --end now --start end-1w --units-exponent 0 DEF:xxx=rrd/%s.rrd:xxx:AVERAGE LINE2:xxx#FF0000' % (fn, fn, )
					print(cmd)
					subprocess.check_call(cmd, shell=True)

					cmd = 'rrdtool graph png/%s__1m.png --end now --start end-1M --units-exponent 0 DEF:xxx=rrd/%s.rrd:xxx:AVERAGE LINE2:xxx#FF0000' % (fn, fn, )
					print(cmd)
					subprocess.check_call(cmd, shell=True)
				#endif

				last_vals[k] = v
			#endwhile

			time.sleep(1)  # TODO: hard-coded shit
		#endwhile

		logging.info('thread exit')
	#enddef

	def quit(self):
		self._run = False
	#enddef
#endclass

# TODO: globals are shit!!!
alerts = load_alerts('alerts.conf')

def main():
	args = docopt.docopt(__doc__, version=__version__)

	logging.basicConfig(level='DEBUG')

	global data, evts, last_vals

	if os.path.isfile('state.json'):
		logging.info('loading state from state.json')
		s = load_json('state.json')
		data = s.get('data', data)
		evts = s.get('evts', evts)
		last_vals = s.get('last_vals', last_vals)
	#endif

	thr = MyThread()
	thr.start()

	app.run(host='::', threaded=True)

	thr.quit()
	thr.join()

	logging.info('saving state to state.json')
	s = {}
	s['data'] = data
	s['evts'] = evts
	s['last_vals'] = last_vals
	save_json(s, 'state.json')

	logging.info('exit')
#enddef

if __name__ == '__main__':
	sys.exit(main())
#endif
