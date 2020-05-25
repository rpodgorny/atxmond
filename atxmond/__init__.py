#!/usr/bin/python3

'''
atxmond.

Usage:
  atxmond [options]

Options:
  -c <fn>             Path to the configuration file.
  --alerts <fn>       Path to the alerts file.
  --events <fn>       Path to the events file.
  --state <fn>        Path to the state file.
  --port <port>       Port number to listen on.
  --db <host>         Hostname of mongodb backend.
  --collection <col>  Collection to use in mongo.
  --debug             Set log level to DEBUG.
'''

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
from configparser import ConfigParser


__version__ = '0.0'


HISTORY_LEN = 10
RRD = False
GEN_PNG = False


# TODO: globals are shit
app = flask.Flask(__name__)
db = None
data = []
evts = []  # TODO: this is shitty name
lasts = {}  # TODO: shitty name


# TODO: ugly name, ugly functionality
def normalize(s):
	return s.replace('/', '__').replace(' ', '_').replace(':', '_')


def load_json(fn):
	with open(fn, 'r') as f:
		return json.load(f)


def save_json(data, fn):
	with open(fn, 'w') as f:
		return json.dump(data, f, indent=2)


def load_alerts(fn):
	ret = []
	with open(fn, 'r') as f:
		for line in f:
			line = line.strip()
			if not line:
				continue
			reg_exp, operator, value = line.split(' ')
			value = int(value)
			ret.append((reg_exp, operator, value))
	return ret


def load_events(fn):
	ret = []
	with open(fn, 'r') as f:
		for line in f:
			line = line.strip()
			if not line:
				continue
			reg_exp, operator, value = line.split(' ')
			value = int(value)
			ret.append((reg_exp, operator, value))
	return ret


@app.route('/')
def index():
	return '<html><body><a href="/show">show</a></body></html>'


@app.route('/save', methods=['GET', 'POST'])
def save():
	d = flask.request.get_json(force=True)
	t = time.time()
	if isinstance(d, dict):
		d = [d, ]
	if isinstance(d, list):
		logging.debug('will save %s entries' % len(d))
		for i in d:
			i = handle_legacy(i)
			i['t_server'] = t
			db.data.insert_one(i)
			data.append(i)
		return 'ok'
	else:
		return 'unknown data format (%s)' % type(d)


@app.route('/show')
def show():
	x = []
	# TODO: find the actual query to find unique shit
	for k in sorted(db.data.distinct('k')):
		i = db.data.find({'k': k}).sort([('t', -1), ])[0]
		x.append(i)
	return flask.render_template('show.html', data_last=x)


@app.route('/graph/<path:k>/<int:secs>')
def graph(k, secs):
	x = []
	since = time.time() - secs
	for i in db.data.find({'k': k, 't': {'$gte': since}}).sort([('t', 1), ]):
		x.append(i)
	return flask.render_template('graph.html', data=x)


@app.route('/alerts')
def alerts():
	x = []
	for reg_exp, operator, value in alerts:
		print(lasts)
		for k in sorted(db.data.distinct('k')):
			if not re.match(reg_exp, k):
				continue
			doc = db.data.find({'k': k}).sort([('t', -1), ])[0]
			if operator == '==':
				if doc['v'] != value:
					continue
			elif operator == '!=':
				if doc['v'] == value:
					continue
			else:
				raise Exception('unknown operator %s' % operator)
			#t = datetime.datetime.fromtimestamp(t).strftime('%Y-%m-%d %H:%M:%S')
			x.append(doc)
	return flask.render_template('alerts.html', data_last=x)


@app.route('/events')
def events():
	x = []
	for i in evts:
		x.append(i)
	return flask.render_template('events.html', data_last=x)


@app.route('/show_last/<path:k>')
def show_last(k):
	x = []
	# TODO: actually show the last HISTORY_LEN ones
	for i in db.data.find({'k': k}).sort([('t', 1), ]).limit(HISTORY_LEN):
		x.append(i)
	return flask.render_template('show_last.html', data_last=x)


def handle_legacy(d):
	if 'path' in d:
		d['k'] = d['path']
		del d['path']
	if 'value' in d:
		d['v'] = d['value']
		del d['value']
	if 'time' in d:
		d['t'] = d['time']
		del d['time']
	return d


def rrd(d):
	fn = normalize(d['k'])
	if not os.path.isfile('rrd/%s.rrd' % fn):
		cmd = 'rrdtool create rrd/%s.rrd --start 0 --step %d DS:xxx:GAUGE:%d:U:U' % (fn, d['interval'], d['interval'] * 2)
		cmd += ' RRA:AVERAGE:0.999:1:100 RRA:AVERAGE:0.999:100:100'
		logging.debug(cmd)
		subprocess.check_call(cmd, shell=True)
	#cmd = 'rrdtool update rrd/%s.rrd %d:%s' % (fn, int(d['t'] - 1), d['v'])
	#logging.debug(cmd)
	#subprocess.check_call(cmd, shell=True)
	cmd = 'rrdtool update rrd/%s.rrd %d:%s' % (fn, int(d['t']), d['v'])
	logging.debug(cmd)
	subprocess.check_call(cmd, shell=True)
	if GEN_PNG:
		cmd = 'rrdtool graph png/%s__10min.png --end now --start end-10m --units-exponent 0 DEF:xxx=rrd/%s.rrd:xxx:AVERAGE LINE2:xxx#FF0000' % (fn, fn, )
		logging.debug(cmd)
		subprocess.check_call(cmd, shell=True)
		cmd = 'rrdtool graph png/%s__1h.png --end now --start end-1h --units-exponent 0 DEF:xxx=rrd/%s.rrd:xxx:AVERAGE LINE2:xxx#FF0000' % (fn, fn, )
		logging.debug(cmd)
		subprocess.check_call(cmd, shell=True)
		cmd = 'rrdtool graph png/%s__1d.png --end now --start end-1d --units-exponent 0 DEF:xxx=rrd/%s.rrd:xxx:AVERAGE LINE2:xxx#FF0000' % (fn, fn, )
		logging.debug(cmd)
		subprocess.check_call(cmd, shell=True)
		cmd = 'rrdtool graph png/%s__1w.png --end now --start end-1w --units-exponent 0 DEF:xxx=rrd/%s.rrd:xxx:AVERAGE LINE2:xxx#FF0000' % (fn, fn, )
		logging.debug(cmd)
		subprocess.check_call(cmd, shell=True)
		cmd = 'rrdtool graph png/%s__1m.png --end now --start end-1M --units-exponent 0 DEF:xxx=rrd/%s.rrd:xxx:AVERAGE LINE2:xxx#FF0000' % (fn, fn, )
		logging.debug(cmd)
		subprocess.check_call(cmd, shell=True)


class MyThread(threading.Thread):
	def __init__(self, events_fn):
		threading.Thread.__init__(self, daemon=False)
		self.events_fn = events_fn
		self._run = True

	def run(self):
		logging.info('thread run')
		events = load_events(self.events_fn)
		while self._run:
			while data:
				i = data.pop(0)
				logging.debug('data: %s' % i)
				last = lasts.get(i['k'], {})
				if i['v'] != last.get('v'):
					logging.debug('change: %s' % i)
					db.changes.insert_one(i)
					for reg_exp, operator, value in events:
						if not re.match(reg_exp, i['k']):
							continue
						if operator == '==':
							if i['v'] != value:
								continue
						elif operator == '!=':
							if i['v'] == value:
								continue
						else:
							raise Exception('unknown operator %s' % operator)
						logging.debug('new event: %s %s' % (i['k'], i['v']))
						evts.append(i)
				if RRD:
					rrd(i)
				lasts[i['k']] = i
			time.sleep(1)  # TODO: hard-coded shit
		logging.info('thread exit')

	def quit(self):
		self._run = False

# TODO: globals are shit!!!
alerts = None

def main():
	args = docopt.docopt(__doc__, version=__version__)

	level = 'DEBUG' if args['--debug'] else 'INFO'
	logging.basicConfig(level=level)

	cfg_fn = args['-c']
	if not cfg_fn:
		for fn in ('etc/atxmond.conf', '/etc/atxmond/atxmond.conf'):
			if not os.path.isfile(fn):
				continue
			cfg_fn = fn
			break

	alerts_fn = args['--alerts']
	if not alerts_fn:
		for fn in ('etc/alerts.conf', '/etc/atxmond/alerts.conf'):
			if not os.path.isfile(fn):
				continue
			alerts_fn = fn
			break

	events_fn = args['--events']
	if not events_fn:
		for fn in ('etc/events.conf', '/etc/atxmond/events.conf'):
			if not os.path.isfile(fn):
				continue
			events_fn = fn
			break

	state_fn = args['--state']
	if not state_fn:
		for fn in ('state.json', '/var/lib/atxmond/state.json'):
			if not os.path.isfile(fn):
				continue
			state_fn = fn
			break

	global alerts
	alerts = load_alerts(alerts_fn)

	global data, evts, lasts

	if state_fn and os.path.isfile(state_fn):
		logging.info('loading state from %s' % state_fn)
		s = load_json(state_fn)
		data = s.get('data', data)
		evts = s.get('evts', evts)
		lasts = s.get('lasts', lasts)

	cfg = ConfigParser()
	cfg.read(cfg_fn)

	try:
		port = int(args['--port'])
	except:
		port = None
	if port is None:
		port = cfg.getint('General', 'Port', fallback=None)
	logging.info('will run on port %d' % port)

	db_host = args['--db']
	logging.info('will connect to %s' % db_host)

	collection_name = args['--collection']
	if collection_name is None:
		collection_name = cfg.get('Mongo', 'Collection')
	logging.info('will use collection %s' % collection_name)

	# TODO: ugly
	global db
	db = pymongo.MongoClient(db_host)[collection_name]

	db.data.ensure_index('k')
	db.data.ensure_index('t')
	db.data.ensure_index([('k', 1), ('v', 1)])
	db.data.ensure_index([('k', 1), ('t', 1)])
	db.data.ensure_index([('k', 1), ('v', 1), ('t', 1)])
	db.changes.ensure_index('k')
	db.changes.ensure_index('t')

	thr = MyThread(events_fn)
	thr.start()

	app.run('::', port, threaded=True)

	thr.quit()
	thr.join()

	logging.info('saving state to %s' % state_fn)
	s = {}
	s['data'] = data
	s['evts'] = evts
	s['lasts'] = lasts
	save_json(s, state_fn)

	logging.info('exit')


if __name__ == '__main__':
	sys.exit(main())
