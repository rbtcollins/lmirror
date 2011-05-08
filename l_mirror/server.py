#
# LMirror is Copyright (C) 2010 Robert Collins <robertc@robertcollins.net>
# 
# LMirror is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
# 
# This program is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE.  See the GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License along with
# this program.  If not, see <http://www.gnu.org/licenses/>.
# 
# In the LMirror source tree the file COPYING.txt contains the GNU General Public
# License version 3.
# 

"""Server, the smart server for serving mirror sets."""

__all__ = ['Server', 'SetWatcher']

import json
import logging
import os
import threading
from time import time

from paste import fileapp, httpexceptions, httpserver
from paste.httpexceptions import HTTPExceptionHandler
from paste.httpheaders import *
try:
    import pyinotify
except ImportError:
    pyinotify = None

from bzrlib import urlutils
from bzrlib.errors import NoSuchFile, NotLocalUrl

class Server(object):
    """A server of mirror sets.

    Servers are created with a ui object which is used for logging over the
    lifetime of the server.

    Typical use is:
       >>> s = Server(ui)
       >>> s.start()
       >>> s.add(a_mirrorset)
       >>> s.stop()

    :ivar addresses: A list of the addresses (as urls) that this server can be
        contacted on.
    :ivar mirrorsets: A dict name->MirrorSet containing the mirror sets being
        served.
    :ivar ui: An l_mirror.ui.AbstractUI to report via.
    :ivar set_watcher: A SetWatcher if inotify is enabled, or None.
    """

    def __init__(self, ui):
        """Create a Server reporting to ui."""
        self.ui = ui
        self.addresses = []
        self.mirrorsets = {}
        logger = logging.getLogger('paste.httpserver.ThreadPool')
        # Set a decent level for paste
        logger.setLevel(logging.INFO)
        self.set_watcher = None

    def start(self, port=8080):
        """Start the server.

        This starts a server thread to run the server. Call stop() to stop
        listening and shutdown the server.
        """
        app = HTTPExceptionHandler(_RootApp(self))
        self._server = httpserver.serve(app, host='0.0.0.0', port=port,
            start_loop=False)
        port = self._server.server_port
        url = 'http://127.0.0.1:%s/' % port
        self.addresses.append(url)
        self.ui.output_values([('url', url)])
        self._server_thread = threading.Thread(target=self._server.serve_forever)
        self._server_thread.start()

    def stop(self):
        """Stop the server. This completes active requests cleanly."""
        self._server.server_close()
        self._server_thread.join()

    def add(self, mirrorset):
        """Add mirrorset to the mirror sets being served."""
        if mirrorset.name in self.mirrorsets:
            raise ValueError('already serving %s' % mirrorset.name)
        self.mirrorsets[mirrorset.name] = mirrorset


class _RootApp(object):
    """WSGI App for serving mirror sets.
    
    :ivar server: A lmirror.server.Server instance containing server state.
    """

    SETS_PREFIX = '/.lmirror/sets/' # Must match disk layout
    METADATA_PREFIX = '/metadata/'
    CONTENT_PREFIX = '/content/'
    STREAM_PREFIX = '/stream/'
    CHANGES_PREFIX = '/changes/'
    UPDATED_PREFIX = '/updated/'


    def __init__(self, server):
        """Create a WSGI with Server server."""
        self.server = server

    def _check_name(self, name):
        if name not in self.server.mirrorsets:
            raise httpexceptions.HTTPNotFound()
        return self.server.mirrorsets[name]

    def _parse_url(self, path):
            elements = path.split('/')
            if len(elements) < 3:
                raise httpexceptions.HTTPNotFound()
            if '..' in elements:
                raise httpexceptions.HTTPNotFound()
            name = elements[2]
            mirrorset = self._check_name(name)
            return mirrorset, elements[3:]

    def __call__(self, environ, start_response):
        """WSGI serve-a-response interface - dispatches to different urls."""
        path = environ['PATH_INFO']
        # format probes
        if path.startswith(self.SETS_PREFIX):
            name = path[len(self.SETS_PREFIX):].split('/')[0]
            self._check_name(name)
            if path.endswith('/format'):
                app = fileapp.DataApp('LMirror Smart Server 1',
                    content_type='text/plain')
                app.cache_control(public=True, max_age=3600)
                return app(environ, start_response)
            elif path.endswith('/set.conf'):
                mirrorset = self.server.mirrorsets[name]
                app = _TransportFileApp(mirrorset._get_settings_file(), None,
                    content_type='text/plain')
                return app(environ, start_response)
        # metadata retrieval
        if path.startswith(self.METADATA_PREFIX):
            mirrorset, remainder = self._parse_url(path)
            backing = mirrorset._metadatadir()
            basename = remainder[-1]
            for element in remainder[:-1]:
                backing = backing.clone(element)
            app = fileapp.DataApp(backing.get_bytes(basename),
                content_type='text/plain')
            # Journals are not streamed yet:
            if 'journals' in remainder:
                app.cache_control(public=True, max_age=360000)
            return app(environ, start_response)
        # smart content serving - client side checks signatures.
        if path.startswith(self.STREAM_PREFIX):
            mirrorset, remainder = self._parse_url(path)
            from_journal = int(remainder[0])
            to_journal = int(remainder[1])
            generator = mirrorset.get_generator(from_journal, to_journal)
            return _DynamicApp(generator.as_bytes(),
                content_type='application/x-lmirror')(environ, start_response)
        # inotify infterface.
        if path.startswith(self.CHANGES_PREFIX):
            mirrorset, remainder = self._parse_url(path)
            if self.server.set_watcher is None:
                raise httpexceptions.HTTPServiceUnavailable("No inotify thread.")
            changes = self.server.set_watcher.get_changes(mirrorset)
            if changes is None:
                raise httpexceptions.HTTPNotFound(
                    "Not ready to answer from inotify cache.")
            changes_bytes = json.dumps(changes)
            app = fileapp.DataApp(changes_bytes, content_type='application/json')
            app.cache_control(public=None, max_age=0)
            return app(environ, start_response)
        # updates to a mirror: when a mirror has had a new changeset added,
        # etc. Causes inotify cached data to be dropped. This isn't a POST at
        # the moment because the http client we're using doesn't make that as
        # easy as it might.
        if path.startswith(self.UPDATED_PREFIX):
            mirrorset, remainder = self._parse_url(path)
            if self.server.set_watcher is not None:
                self.server.set_watcher.mirror_updated(mirrorset)
            app = fileapp.DataApp('', content_type='text/plain')
            return app(environ, start_response)
        # fallback to vanilla content.
        if path.startswith(self.CONTENT_PREFIX):
            mirrorset, remainder = self._parse_url(path)
            backing = mirrorset._contentdir()
            basename = remainder[-1]
            for element in remainder[:-1]:
                backing = backing.clone(element)
            # strictly speaking the content type is wrong.
            content_file = backing.get(basename)
            content_length = backing.stat(basename).st_size
            # stream
            app = _TransportFileApp(content_file, content_length,
                content_type='text/plain')
            # Permit content files to be cached: lmirror clients currently
            # prevent caching, and when they do permit it they will know
            # how to re-request.
            if 'journals' in remainder:
                app.cache_control(public=True, max_age=360000)
            return app(environ, start_response)
        raise httpexceptions.HTTPNotFound()


class _DynamicApp(object):
    """A dynamically generated content app."""

    def __init__(self, bytes_generator, **kwargs):
        headers = []
        for (k, v) in kwargs.items():
            header = get_header(k)
            header.update(headers, v)
        CONTENT_TYPE.update(headers)
        self.headers = headers
        self.cache_control(public=True, max_age=360000)
        self.generator = bytes_generator

    def cache_control(self, **kwargs):
        self.expires = CACHE_CONTROL.apply(self.headers, **kwargs) or None
        return self

    def __call__(self, environ, start_response):
        start_response('200 OK', self.headers)
        return self.generator


class _TransportFileApp(fileapp.DataApp):
    """An adapter to bzrlib transports.

    This is rarely used due to the streaming facility.
    
    This does not support ETags or IMS yet; it could if desired in the future,
    but as lmirror only requests content it needs there isn't much call for
    this. What would be good would be to is to generate a sha1 ETAG as a
    trailer, in the future, and thus work with caches.

    Likewise, range requests are not supported - that would be easy enough to
    do, see fileapp.DataApp.get().
    """

    def __init__(self, content_file, content_length, **kwargs):
        fileapp.DataApp.__init__(self, None, **kwargs)
        self.content_file = content_file
        self.content_length = content_length

    def get(self, environ, start_response):
        is_head = environ['REQUEST_METHOD'].upper() == 'HEAD'
        headers = self.headers[:]
        if self.content_length is not None:
            CONTENT_LENGTH.update(headers, self.content_length)
        start_response('200 OK', headers)
        if is_head:
            return ['']
        self.content_file.seek(0)
        return fileapp._FileIter(self.content_file, size=self.content_length)


class SetWatcher(object):
    """Watch sets using inotify.
    
    This class watches all the files in one or more sets using inotify. This
    requires an inotify watch on every directory that is in the set. Currently
    it watches every directory under the content root; in future it might 
    honour excludes.
    
    SetWatcher then records all the mutation events that occur within these
    directories. Each set has a scan date for it; when the time that an event
    was received is older than the oldest date for a set, the event is
    discarded. As a consequence, failing to update a monitored set can prevent
    memory being released.

    Currently, events are just held in a dict, so pruning is an O(events) task.
    """

    def __init__(self):
        """Create a SetWatcher.

        This creates a WatchManager and other pyinotify objects itself.
        """
        self.wm = pyinotify.WatchManager()
        self.handler = GatherDirectories(self)
        self.notifier = pyinotify.Notifier(self.wm, default_proc_fun=self.handler)
        self.mirrorsets = {}
        self.paths = {}
        self.changes = {} # path -> latest timestamp
        # path cleanups need to be locked so that a cleanup doesn't delete something
        # that is simultaneously changing.
        self.changes_lock = threading.Lock()

    def add(self, mirror):
        """Add mirror to be observed for changes."""
        try:
            path = mirror._contentdir().local_abspath('.')
        except NotLocalUrl:
            return
        self.paths.setdefault(path, []).append(mirror)
        # Add the directories recursively: to disowe can't depend on dir opens to
        # start traversing, because processes might be active below the top
        # when we
        # are adding the mirror.
        # TODO: be more precise about events. Our goal is to be able to list
        # directories that need examining for changes; new directories will be
        # discovered by a change to the parent, so we don't need to recurse
        # into them. So we need any write operations logged, is all.
        # The reason we don't record all changed files is simply to tradeoff
        # against the memory overhead of remembering everthing. This may be a
        # mistake.
        wanted_events = (
            pyinotify.IN_MODIFY |
            pyinotify.IN_ATTRIB |
            pyinotify.IN_CLOSE_WRITE |
            pyinotify.IN_MOVED_FROM |
            pyinotify.IN_MOVED_TO |
            pyinotify.IN_CREATE |
            pyinotify.IN_DELETE |
            pyinotify.IN_DELETE_SELF |
            pyinotify.IN_MOVE_SELF |
            pyinotify.IN_ONLYDIR | # New in 2.6.15; perhaps make it optional?
            # Should be only watching dirs, belt and bracers.
            pyinotify.IN_DONT_FOLLOW )
        metadata = mirror._get_metadata()
        last = float(metadata.get('metadata', 'timestamp'))
        for dirname, dirs, files in os.walk(path):
            self.wm.add_watch(dirname, wanted_events)
            for child in dirs + files:
                fullpath = dirname + '/' + child
                mtime = os.lstat(fullpath).st_mtime
                if mtime >= last:
                    # records with time.time, but thats ok, newer times won't
                    # reduce accuracy.
                    self.note_changed(fullpath)
        # Make this mirrorset usable in the getchanges API.
        self.mirrorsets[mirror.name] = mirror

    def note_changed(self, path):
        self.changes_lock.acquire()
        try:
            self.changes[path] = time()
        finally:
            self.changes_lock.release()

    def get_changes(self, mirror):
        """Get a list of all the paths changed that might be in mirror.
        
        :return: None if the mirror is not able to be answered from
            self.changes, or a list of the paths that might be chagned in the
            mirror.
        """
        # TODO: filter for the caller to one mirror
        if mirror.name not in self.mirrorsets:
            return None
        self.changes_lock.acquire()
        try:
            try:
                basepath = mirror._contentdir().local_abspath('.')
            except NotLocalUrl:
                return None
            return [path for path in self.changes if path.startswith(basepath)]
        finally:
            self.changes_lock.release()

    def mirror_updated(self, mirror):
        """Cleanup changes for mirror that are older than mirror."""
        # TODO: make use of the fact different mirrors may have different paths
        # rather than looking at all mirrors for all paths.
        if not self.mirrorsets:
            return
        self.changes_lock.acquire()
        try:
            last = None
            for mirror in self.mirrorsets.values():
                metadata = mirror._get_metadata()
                if last is None:
                    last = float(metadata.get('metadata', 'timestamp'))
                else:
                    last = min(last, float(metadata.get('metadata', 'timestamp')))
            for path, timestamp in list(self.changes.items()):
                if timestamp < last:
                    del self.changes[path]
        finally:
            self.changes_lock.release()


if pyinotify is not None:
    class GatherDirectories(pyinotify.ProcessEvent):
        """Gather directories for a set watcher."""

        def __init__(self, set_watcher):
            """Create a GatherDirectories gathering to a SetWatcher."""
            self.set_watcher = set_watcher

        def process_default(self, event):
            self.set_watcher.note_changed(event.pathname)
