"""
Bus animation

author: Mike Boos
email: mike.boos@gmail.com

Based on:
Matplotlib Animation Example
author: Jake Vanderplas
email: vanderplas@astro.washington.edu
website: http://jakevdp.github.com
license: BSD
"""

import psycopg2
import numpy as np
from matplotlib import pyplot as plt
from matplotlib import animation

import argparse

parser = argparse.ArgumentParser(description='Generate new GTFS rows based on estimates of future service.')
parser.add_argument('-b', '--bounds', dest='bounds', default=[-80.61, -80.25, 43.32, 43.61], nargs=4,
		   help='lat/lon boundaries [lonWest, lonEast, latSouth, latNorth]')
parser.add_argument('-u', '--user', dest='user', required=True,
		   help='username for database')
parser.add_argument('-d', '--db', dest='db', required=True,
		   help='database')
parser.add_argument('-o', '--output', dest='outfile', required=True,
		   help='output video file')
parser.add_argument('-s', '--service', dest='service', required=True,
		   help='service id')

args = parser.parse_args()

conn = psycopg2.connect("dbname=%s user=%s" % (args.db, args.user))
cur = conn.cursor()

fig = plt.figure()
fig.subplots_adjust(left=-0.05, right=1.05, bottom=-0.05, top=1.05)
ax = fig.add_subplot(111, 
                     xlim=(args.bounds[0], args.bounds[1]), ylim=(args.bounds[2], args.bounds[3]))
ax.set_axis_bgcolor("#000000") 
time_text = ax.text(0.1, 0.1, '', transform=ax.transAxes, color='w')

line = {}
cur.execute("""SELECT route_id from routes""")
trips = cur.fetchall()
for i,trip in enumerate(trips):
	line[trip[0]], = ax.plot([], [], '.', mfc=plt.cm.hsv(int(i*1.8)), ms=9)


# initialization function: plot the background of each frame
def init():
    for l in line.values():
    	l.set_data([],[])
    time_text.set_text('')
    print 'initiating animation...'
    return tuple(line.values()) + (time_text,)
    
# animation function.  This is called sequentially
def animate(i):
    x = {}
    y = {}
    for k in line.keys():
    	x[k] = []
    	y[k] = []
    min, sec = divmod(i, 12)
    hr, min = divmod(min, 60)
    sec *= 5
    hr += 5
    ts = "%02d:%02d:%02d" % (hr,min,sec) 
    print ts
    cur.execute("""SELECT ST_X(gg.g), ST_Y(gg.g), rid FROM
		(SELECT ST_Line_Interpolate_Point(patterns.geom,
				(ts.t - ts.t1)/(ts.t2 - ts.t1)*(ts.st2 - ts.st1) + ts.st1) as g, rid
			FROM patterns,
			(SELECT trips.shape_id as sid, trips.route_id as rid,
				extract(epoch from to_timestamp((%s), 'hh24:mi:ss')) as t, 
				extract(epoch from to_timestamp(s1.departure_time, 'hh24:mi:ss')) as t1,
				extract(epoch from to_timestamp(s2.arrival_time, 'hh24:mi:ss')) as t2, 
				s1.shape_traveled as st1, s2.shape_traveled as st2
				FROM  trips, stop_times s1, stop_times s2
				WHERE trips.service_id =  '%s'
				AND trips.trip_id = s1.trip_id AND trips.trip_id = s2.trip_id 
				AND s1.stop_sequence + 1 = s2.stop_sequence
				AND s1.arrival_time < (%s) AND s2.arrival_time >= (%s)) as ts
			WHERE (ts.t1 < ts.t AND ts.t2 >= ts.t) 
			AND ts.sid = patterns.shape_id) as gg """, [ts,args.service,ts,ts])
    buses = cur.fetchall()
    
    for bus in buses:
      x[bus[2]].append(bus[0])
      y[bus[2]].append(bus[1])
    
    for k in line.keys():
    	line[k].set_data(x[k], y[k])
    time_text.set_text(ts)
    return tuple(line.values()) + (time_text,)




# call the animator.  blit=True means only re-draw the parts that have changed.
anim = animation.FuncAnimation(fig, animate, init_func=init,
                               frames=(60*12*21), interval=20, blit=True)

print 'saving to file...'
# save the animation as an mp4.  This requires ffmpeg or mencoder to be
# installed.  The extra_args ensure that the x264 codec is used, so that
# the video can be embedded in html5.  You may need to adjust this for
# your system: for more information, see
# http://matplotlib.sourceforge.net/api/animation_api.html
anim.save(args.outfile, fps=30, extra_args=['-vcodec', 'libx264'])

