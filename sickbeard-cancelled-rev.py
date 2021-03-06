#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# <derkens@gmail.com>
# show cancelled? this script notifies you and put the show in 'pause' (after the last ep oc.)
#
# shamelessly incorporated stuff from Sick Beard AutoProcessTV
# Author: Nic Wolfe <nic@wolfeden.ca>
# URL: http://code.google.com/p/sickbeard/
import requests
import json
from pprint import pprint


import os.path
import sys, json
import lib.logger.logger as logger
import lib.config as config
import lib.emailer as emailer
import lib.misc as misc
import lib.api as api
sys.excepthook = misc.log_uncaught_exceptions

indexer, fork = api.sick_call_initial()

if config.use_email:
    text_file = open("Output.txt", "w")

logger.logging.info("Opening connection to " + fork)
params = {'cmd': 'shows', 'sort': 'name', 'paused': '0'}
res = api.sick_call(params)


end = filter(lambda x: x['status'] == 'Ended', res['data'].values())
logger.logging.debug(json.dumps(end, indent=4))

if end == []:
    logger.logging.info("Nothing to be done, exiting")

for i in end:
    showname = i['show_name'].encode('utf-8'); logger.logging.debug("Showname = " + showname)
    #print showname
    iid = i['indexerid']
    geturl = ("http://localhost:8182/api/<API>/?cmd=show.stats&indexerid=%s") % iid
    response = requests.get(geturl)
    data = response.json()
    #pprint(data)
    dl = data['data']['downloaded']['total']
    sn =  data['data']['snatched']['total']
    tot =  data['data']['total']
    #print dl, sn, tot
    stat = i['status']; logger.logging.debug("Show status = " + stat)
    net = i['next_ep_airdate']; logger.logging.debug("Next episode date = " + net)
    logger.logging.info(showname + " has status: " + stat)
    if net == '' and (tot - dl == 0) and sn == 0 and iid != 72493:
        params = {'cmd': 'shows', 'sort': 'name'}
        res = api.sick_call(params)
        sickid = res['data'][showname][indexer]
        #logger.logging.debug(showname + " has " + indexer + " " + str(sickid))
        params = {'cmd': 'show.pause', indexer: sickid, 'pause': 1}
        res = api.sick_call(params)

        args = {'showname': showname}
        pushtitle, pushmsg = misc.replace(config.sbca_push_title, config.sbca_push_msg, **args)

        if config.use_pushover:
            push_info = {'potitle': pushtitle, 'pomsg': pushmsg, 'sound': config.sbca_push_sound}
            api.pushover(config.user_key, config.app_token, config.push_device, **push_info)
        if config.use_nma:
            logger.logging.debug("Sending NMA notification...")
            from lib.pynma import pynma
            p = pynma.PyNMA(config.nma_api)
            res = p.push(config.app, pushtitle, pushmsg, 0, 1, config.nma_priority)
            if res[config.nma_api][u'code'] == u'200':
                logger.logging.info("NMA Notification succesfully send")
            else:
                error = res[config.nma_api]['message'].encode('ascii')
                logger.logging.error("NMA Notification failed: " + error)
        if config.use_pushbullet:
            push_info = pushtitle, pushmsg, config.deviceid, config.channeltag
            api.pushbullet(push_info)
        if config.use_email:
            text_file.write(show + " is possibly cancelled\n")
    elif net == '' and ((tot - dl > 0) or sn > 0):
        params = {'cmd': 'shows', 'sort': 'name'}
        res = api.sick_call(params)
        sickid = res['data'][showname][indexer]
        logger.logging.debug(showname + " has " + indexer + " " + str(sickid))
        params = {'cmd': 'show.resume', indexer: sickid, 'resume': 1}
        res = api.sick_call(params)
        print "Resuming incomplete show...."
    elif iid==72493:
        print "skipping problem show..."

    else:
        print 'Incomplete skipped...'

if config.use_email:
    text_file.close()
    logger.logging.info("Sending Email notification...")
    emailer.SendEmail(show)
    os.remove("Output.txt")

misc.access_log_for_all()
