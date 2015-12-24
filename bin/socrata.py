# /usr/bin/env python
welcomeText = '''#
# hire.vladimir@gmail.com
#
# allows dataset pulls from https://opendata.socrata.com/ into Splunk
#
# rev. history
# 12/21/15 1.0 initial write
#
'''
from urllib2 import urlopen, Request, HTTPError, URLError
import sys, time, os, re, json, urllib
import logging, logging.handlers
import splunk.Intersplunk as si

#######################################
# SCRIPT CONFIG
#######################################
# set log level valid options are: (NOTSET will disable logging)
# CRITICAL, ERROR, WARNING, INFO, DEBUG, NOTSET
SPLUNK_HOME = "."
LOG_LEVEL = logging.INFO
LOG_FILE_NAME = "socrata.log"

# socrata specific setings
SOCRATA_AUTH_TOKEN = ""


def setup_logging():  # setup logging
    global SPLUNK_HOME, LOG_LEVEL, LOG_FILE_NAME
    if 'SPLUNK_HOME' in os.environ:
        SPLUNK_HOME = os.environ['SPLUNK_HOME']

    log_format = "%(asctime)s %(levelname)-s\t%(module)s[%(process)d]:%(lineno)d - %(message)s"
    logger = logging.getLogger('v')
    logger.setLevel(LOG_LEVEL)

    l = logging.handlers.RotatingFileHandler(os.path.join(SPLUNK_HOME, 'var', 'log', 'splunk', LOG_FILE_NAME), mode='a', maxBytes=1000000, backupCount=2)
    l.setFormatter(logging.Formatter(log_format))
    logger.addHandler(l)

    # ..and (optionally) output to console
    logH = logging.StreamHandler()
    logH.setFormatter(logging.Formatter(fmt=log_format))
    # logger.addHandler(logH)

    logger.propagate = False
    return logger


def getDataPayload(uri):
    logger.debug("Request uri=\"%s\"" % uri)
    payload = ""
    try:
        payload = urlopen(Request(uri)).read()
        logger.debug('Received payload="%s"' % payload)
    except HTTPError, e:
        response = e.read().replace("\n", "")
        msg = 'HTTP exception was thrown while making request for uri="%s", status_code=%s, for list of socrata status codes see https://dev.socrata.com/docs/response-codes.html e="%s" response="%s"' % (uri, e.code, e, response)
        logger.error(msg)
        sys.stderr.write('%s\n' % msg)
    except URLError, e:
        msg = 'URLError exception was thrown while making request for for uri="%s", reason="%s"' % (uri, e.reason)
        logger.error(msg)
        sys.stderr.write('%s\n' % msg)
    logger.info('function="getDataPayload" action="success" request="%s", bytes_in="%s"' % (uri, len(payload)))
    return payload


def die(msg):
    logger.error(msg)
    exit(msg)


def socrata2splunk(set_payload_info, socrata_data, show_info=False, convert_time=True):
    payload = []
    data = json.loads(socrata_data)

    if show_info:
        row = {key: set_payload_info[key] for key in set_payload_info}
        for field in data:
            row[field] = "%s" % data[field]
            if isinstance(data[field], list) and str(data[field]).startswith('[u', 0, 2):
                row[field] = data[field]
        payload.append(row)
    else:
        for x in data:
            row = {key: set_payload_info[key] for key in set_payload_info}
            for field in x:
                row[field] = x[field]
                if hasattr(x[field], '__iter__'):  # flatten the array
                    for iz in x[field]:
                        row[field + "_" + iz] = "%s" % x[field][iz]
            payload.append(row)

    logger.debug('socrata2splunk data="%s"' % payload)
    return payload


def validate_args(keywords, argvals):
    logger.info('function="validate_args" calling getKeywordsAndOptions keywords="%s" args="%s"' % (str(keywords), str(argvals)))

    # validate args
    ALLOWED_OPTIONS = ['debug', 'append', 'metadata', 'convert_time', 'auth_token', 'select', 'where', 'order', 'group', 'limit', 'offset', 'q', 'query']
    illegal_args = filter(lambda x: x not in ALLOWED_OPTIONS, argvals)
    if len(illegal_args) != 0:
        die("The argument(s) '%s' is invalid. Supported arguments are: %s" % (illegal_args, ALLOWED_OPTIONS))

    # validate keywords
    if len(keywords) > 1:
        die("more then one argument specified; see command for usage details")
    if len(keywords) != 1 or not re.match("^\w{4}\-\w{4}$|^https.*\/resource\/\w{4}\-\w{4}\.(?:json|xml|csv)$", keywords[0]):
        die("dataset not specified, or does not match short-code or API Endpoint URI format")


def make_arg_sub_based_results(argvals, splunk_data):
    for r in argvals:
        for a in splunk_data[0]:  # assumption to use data from first row.. might need to enhance in future
            if argvals[r] == a:
                logger.debug("found substitution oppty, setting %s=%s" % (r, splunk_data[0][a]))
                argvals[r] = splunk_data[0][a]
    logger.debug("function=make_arg_sub_based_results effective args=\"%s\"" % str(argvals))
    return argvals


def arg_on_and_enabled(argvals, arg, rex=None, is_bool=False):
    result = False

    if is_bool:
        rex = "^(?:t|true|1|yes)$"

    if (rex is None and arg in argvals) or (arg in argvals and re.match(rex, argvals[arg])):
        result = True
    return result

if __name__ == '__main__':
    logger = setup_logging()
    logger.info('starting..')
    eStart = time.time()
    try:
        # si.getKeywordsAndOptions() is "not great.."
        # keywords, argvals = si.getKeywordsAndOptions()
        keywords = filter(lambda x: not re.findall("^\w+=|socrata.py$", x), sys.argv)
        argvals = dict(u.split("=", 1) for u in filter(lambda x: re.findall("^\w+=", x), sys.argv))
        if arg_on_and_enabled(argvals, "debug", is_bool=True):
            logger.setLevel(logging.DEBUG)

        validate_args(keywords, argvals)

        results = si.readResults(None, None, False)
        if results is not None and len(results) > 0:
            logger.error("gonna sub")
            argvals = make_arg_sub_based_results(argvals, results)

        # if api_key argument is passed to command, use it instead of default
        if arg_on_and_enabled(argvals, "auth_token"):
            SOCRATA_AUTH_TOKEN = argvals["auth_token"]
            logger.debug('setting SOCRATA_AUTH_TOKEN="%s"' % str(SOCRATA_AUTH_TOKEN))

        # query parameters
        socrata_parameters = {"$$app_token": SOCRATA_AUTH_TOKEN}
        socrata_show_info = False

        socrata_supported_parameters = ['select', 'where', 'order', 'group', 'limit', 'offset', 'q', 'query']
        for q in socrata_supported_parameters:
            if q in argvals:
                socrata_parameters["$" + q] = argvals[q]

        uber = []
        if arg_on_and_enabled(argvals, "append", is_bool=True):
            uber = results
            logger.debug("arg=append is set to true, will append to input dataset")

        socrata_code = keywords[0]
        if re.match("^http", socrata_code):
            socrata_uri = "%s?%s" % (re.sub("\.(?:csv|xml)$", ".json", socrata_code), urllib.urlencode(socrata_parameters))
        else:
            socrata_uri = "https://opendata.socrata.com/resource/%s.json?%s" % (socrata_code, urllib.urlencode(socrata_parameters))
            socrata_code = "https://opendata.socrata.com/resource/%s.json" % socrata_code

        if arg_on_and_enabled(argvals, "metadata", is_bool=True):
            logger.info('arg=metadata is set to true, will return feed metadata only; will ignore all other arguments/settings')
            socrata_show_info = True
            # https://data.cityofchicago.org/resource/4ijn-s7e5.json -> https://data.cityofchicago.org/api/views/4ijn-s7e5.json
            socrata_uri = re.sub("resource", "api/views", socrata_uri)
        logger.debug('effective uri="%s"' % socrata_uri)

        set_payload = getDataPayload(socrata_uri)
        set_payload_info = {"socrata_dataset": socrata_code}
        if set_payload is not "":
            uber += socrata2splunk(set_payload_info, set_payload, socrata_show_info)

        # keeping all data into single array is waste of memory; need to figure out how to call outputResults multiple times, without adding header each time
        logger.info('sending events to splunk count="%s"' % len(uber))
        si.outputResults(uber)
    except Exception, e:
        logger.error('error while processing events, exception="%s"' % e)
        si.generateErrorResults(e)
        raise Exception(e)
    finally:
        logger.info('exiting, execution duration=%s seconds' % (time.time() - eStart))
