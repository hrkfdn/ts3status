#!/usr/bin/env python3

import config
import re

from ts3query import TS3Connection
from flask import Flask, render_template, Markup
app = Flask(__name__)

t = TS3Connection(config.hostname, config.port)
spacer_re = re.compile(r"\[([?lcr]?)[sS]pacer[\d]*\](.*)")

def connect():
	t.connect()
	t.login(config.username, config.password)
	t.sendcmd("use sid=1")

def disconnect():
	t.disconnect()

def is_empty(clients):
	if len(clients) == 0:
		return True

	# we don't consider serverquery clients (such as ourself) as
	# "real" clients
	for c in clients:
		if c["client_type"] == 0:
			return False
	return True

def channel_html(chan, clientsinchannel):
	global spacer_re
	name = chan["channel_name"]
	m = spacer_re.match(name)

	classes = ""
	if m is not None:
		if m.group(1) == '':
			name = ""
			classes += " spacer_dashed" if m.group(2) == "---" else ""
			classes += " spacer_dotted" if m.group(2) == "..." else ""
			classes += " spacer_straight" if m.group(2) == "___" else ""

			# catch other spacers
			classes += " spacer_dashed" if (m.group(2) == "-.-" or m.group(2) == "-..") else ""
		else:
			classes += " centered" if m.group(1) == 'c' else ""
			classes += " left" if m.group(1) == 'l' else ""
			classes += " right" if m.group(1) == 'r' else ""
			name = m.group(2)
	else:
		if chan["cid"] == 0 or is_empty(clientsinchannel):
			classes += " chan_empty"
		else:
			classes += " chan_populated"

	result = "<li class=\"" + classes + "\">" + name + "\n"
	return result

def client_html(client):
	classes = "client"
	classes += " client_inputmute" if client["client_input_muted"] else ""
	classes += " client_outputmute" if client["client_output_muted"] else ""
	classes += " client_away" if client["client_away"] == 1 else ""
	return "<li class=\"" + classes + "\">" + client["client_nickname"] + "</li>\n"

def generate_overview(ctree, clients):
	result = ""
	for channel in ctree:
		inchan = clients.listinchannel(channel["cid"])
		result += channel_html(channel, inchan) # opens up a channel li

		# process clients in current channel
		if not is_empty(inchan):
			result += "<ul>\n"
			for client in inchan:
				if client["client_type"] == 0: # only show real clients
					result += client_html(client)
			result += "</ul>\n"

		# process subchannels
		if len(channel["children"]) > 0:
			result += "<ul>\n"
			result += generate_overview(channel["children"], clients)
			result += "</ul>\n"

		result += "</li>\n" # close channel li

	return result

@app.route("/")
def main():
	connect()

	channels = t.getchannels()
	clients = t.getclients("-away -voice -info")
	info = t.getserverinfo()

	disconnect()

	if channels is None or clients is None or info is None:
		return "Connection error."

	out = "<ul>\n" + generate_overview(channels.chanlist[0]["children"], clients) + "</ul>\n"

	return render_template("index.html", 
			server_title=info["virtualserver_name"],
			server_platform=info["virtualserver_platform"],
			server_version=info["virtualserver_version"],
			server_host=config.hostname,
			display_host=config.displayhost,
			overview=Markup(out))

if __name__ == "__main__":
	app.run(debug=True, host='0.0.0.0')
