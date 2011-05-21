#!/usr/bin/env python
# -*- coding: utf-8 -*-

# works under both python2 and python3
# ------
# License: MIT
# Copyright (c) 2011 Kohei Ozaki (eowenr atmark gmail dot com)

import re, os, sys
import subprocess, time

class VideoInfoExtractor:
    _VALIDATE_URL    = r'^http://videolectures.net'
    _VIDEO_PAGE      = r'var flashvars = {\s+?streamer:\s"(rtmp://[^"]+)",\s+?file:\s"([^\.]+)\.\w+?"'
    _META_TITLE_NAME = r'<meta name="title" content="\s*([^"]*?)\s*" />'
    _META_URL_NAME   = r'<link rel="image_src" href="/?([^\/]+)/thumb.jpg" />'
    _ORIG_FILENAME   = r'([^\/]+)$'

    def __init__(self):
        self._body            = ''
        self._server          = ''
        self._filepath        = ''
        self._meta_title_name = ''
        self._meta_url_name   = ''
        self._base_filename   = ''
        self._extracted       = False

    @staticmethod
    def valid_url(url):
        return (re.match(VideoInfoExtractor._VALIDATE_URL, url) is not None)

    def report_video_title(self, title):
        print("[download] Title: %s" % title)

    def extract_filename(self, body):
        metaname = re.search(VideoInfoExtractor._META_TITLE_NAME, body)
        if metaname is not None:
            self._meta_title_name = metaname.group(1)
        metaname = re.search(VideoInfoExtractor._META_URL_NAME, body)
        if metaname is not None:
            self._meta_url_name = metaname.group(1)
        metaname = re.search(VideoInfoExtractor._ORIG_FILENAME, self._filepath)
        if metaname is not None:
            self._base_filename = metaname.group(1)

    def extract_flashvars(self, body):
        flashvars = re.search(VideoInfoExtractor._VIDEO_PAGE, body)
        if flashvars is None:
            self._extracted = False
        else:
            self._extracted = True
            self._server = flashvars.group(1)
            self._filepath = flashvars.group(2)

    def get_info(self, url):
        try:
            from urllib import request as urllib_request
        except ImportError:
            import urllib as urllib_request
            pass

        if not self.valid_url(url):
            return False
        conn = urllib_request.urlopen(url)
        self._body = conn.read().decode('utf8')
        self.extract_flashvars(self._body)
        self.extract_filename(self._body)
        self.report_video_title(self._meta_title_name)
        return self._extracted

class DownloadError(Exception): pass
class ExtractionError(Exception): pass

class VideoDownloader:
    PLAYER_URL      = 'http://media.videolectures.net/jw-player/player.swf'
    PLAYER_CHECKSUM = 'e2436d6201f4265a0a0ad974165a3b26a6f302ba8e7cfebd6dfad2cac28105e1'

    def __init__(self, opts):
        self.init = 0
        self.ie   = VideoInfoExtractor()
        self.opts = opts

    def to_stderr(self, mesg):
        print >>sys.stderr, mesg

    def to_stdout(self, mesg, skip_eol=False):
        sys.stdout.write(("%s%s" % (mesg, ["\n",""][skip_eol])))
        sys.stdout.flush()

    def ie_error(self, mesg=None):
        if mesg is not None:
            self.to_stderr(mesg)
        raise ExtractionError(mesg)

    def error(self, mesg=None):
        if mesg is not None:
            self.to_stderr(mesg)
        raise Exception(mesg)

    def report(self, mesg):
        print(mesg)

    def report_download_file(self, filename):
        self.to_stdout("[download] Destination: %s" % filename)

    def download_with_rtmp(self, filename, server, url):
        self.report_download_file(filename)
        try:
            stdout = open(os.path.devnull, 'w')
            subprocess.call(['rtmpdump', '-h'], stdout=stdout, stderr=subprocess.STDOUT)
        except (OSError, IOError):
            self.error('ERROR: rtmpdump could not be run. please check the binary path.')
        finally:
            stdout.close()

        basic_args = ['rtmpdump', '-q', '-r', server, '-y', url, '-a', 'video'] + \
            ['-s', self.PLAYER_URL, '-w', self.PLAYER_CHECKSUM, '-o', filename]
        retval = subprocess.Popen(basic_args)
        while True:
            if retval.poll() != None: break
            if not os.path.exists(filename): continue
            prevsize = os.path.getsize(filename)
            self.to_stdout('\r[rtmpdump] %s bytes' % prevsize, skip_eol=True)
            time.sleep(2.0)
            cursize = os.path.getsize(filename)
            if prevsize != 0 and prevsize == cursize: break

        if retval.wait() == 0:
            self.to_stdout('\r[rtmpdump] %s bytes' % os.path.getsize(filename))
            return True
        else:
            self.error('ERROR: download may be incomplete. rtmpdump exited with code 1 or 2')
            return False

    def get_video(self, url):
        if not self.ie.get_info(url):
            self.ie_error('ERROR: no video information is extracted.')

        if self.opts.usetitle or self.opts.useliteral:
            filename = "%s.flv" % self.ie._meta_title_name
        else:
            filename = "%s.flv" % self.ie._meta_url_name
        if self.download_with_rtmp(filename, self.ie._server, self.ie._filepath):
            self.report("download complete")

def main(opts, url):
    dl = VideoDownloader(opts)
    dl.get_video(url)
    sys.exit(0)

def test_extraction():
    a = 2
    assert a == 2, "assert 2 is 4"

if __name__ == '__main__':
    import optparse
    usage = 'usage: %prog [options] video_url'
    version = '2011.03.30'
    optparser = optparse.OptionParser(usage=usage, version=version, conflict_handler='resolve')
    optparser.add_option('-h', '--help', action='help',
                         help='print this help text and exit')
    optparser.add_option('-v', '--version', action='version',
                         help='print program version and exit')
    optparser.add_option('-w', '--overwrite', action='store_true', dest='overwrite',
                         help='overwrite an existent file')
    optparser.add_option('-t', '--title', action='store_true', dest='usetitle',
                         help='use title in filename')
    optparser.add_option('-l', '--literal', action='store_true', dest='useliteral',
                         help='use literal title in filename')
    (opts, args) = optparser.parse_args()

    if not len(args) > 0:
        optparser.print_help()
        sys.exit(1)
    main(opts, args[0])