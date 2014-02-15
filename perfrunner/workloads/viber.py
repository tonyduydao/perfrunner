import random
import string
from hashlib import md5

from logger import logger
from couchbase import experimental
experimental.enable()
from txcouchbase.connection import Connection
from twisted.internet import reactor


class ViberIterator(object):

    FIXED_KEY_WIDTH = 12
    RND_FIELD_SIZE = 16
    ALPHABET = string.letters + string.digits

    def __iter__(self):
        return self

    def _id(self, i):
        return '{}'.format(i).zfill(self.FIXED_KEY_WIDTH)

    def _key(self, _id):
        return 'AB_{0}_0'.format(_id)

    def _field(self, _id):
        data = md5(_id).hexdigest()[:16]
        return {'pn': _id, 'nam': 'ViberPhone_{}'.format(data)}


class KeyValueIterator(ViberIterator):

    MIN_FIELDS = 11
    MAX_FIELDS = 22
    BATCH_SIZE = 100

    def __init__(self, num_items):
        self.num_items = num_items

    def _value(self, _id):
        return [
            self._field(_id)
            for _ in range(random.randint(self.MIN_FIELDS, self.MAX_FIELDS))
        ]

    def next(self):
        if self.num_items > 0:
            batch = []
            for _ in range(self.BATCH_SIZE):
                _id = self._id(self.num_items)
                self.num_items -= 1
                batch.append((self._key(_id), self._value(_id)))
            return batch
        else:
            raise StopIteration


class NewFieldIterator(ViberIterator):

    WORKING_SET = 0.5  # 50%
    APPEND_SET = 0.15  # 15%
    BATCH_SIZE = 100

    def __init__(self, num_items):
        self.rnd_num_items = int(self.APPEND_SET * num_items)
        self.num_items = int(self.WORKING_SET * num_items)

    def next(self):
        if self.rnd_num_items > 0:
            batch = []
            for _ in range(self.BATCH_SIZE):
                _id = self._id(random.randint(1, self.num_items))
                field = self._field(_id)
                self.rnd_num_items -= 1
                batch.append((self._key(_id), field))
            return batch
        else:
            raise StopIteration


class WorkloadGen(object):

    NUM_ITERATIONS = 15

    def __init__(self, num_items):
        self.num_items = num_items
        self.kv_iterator = KeyValueIterator(num_items)
        self.field_iterator = NewFieldIterator(num_items)

    def _interrupt(self, err):
        reactor.stop()
        logger.interrupt(err.value)

    def _on_set(self, *args):
        self.counter += 1
        if self.counter == self.kv_iterator.BATCH_SIZE:
            self._set()

    def _set(self, *args):
        self.counter = 0
        try:
            for k, v in self.kv_iterator.next():
                d = self.cb.set(k, v)
                d.addCallback(self._on_set)
                d.addErrback(self._interrupt)
        except StopIteration:
            reactor.stop()

    def load(self, host_port, bucket, password):
        logger.info('Running initial load: {} items'.format(self.num_items))
        host, port = host_port.split(':')

        self.cb = Connection(bucket=bucket, host=host, password=password)
        d = self.cb.connect()
        d.addCallback(self._set)
        d.addErrback(self._interrupt)

        reactor.run()

    def _on_append(self, *args):
        self.counter += 1
        if self.counter == self.field_iterator.BATCH_SIZE:
            self._append()

    def _on_get(self, rv, f):
        v = rv.value
        v.append(f)
        d = self.cb.set(rv.key, v)
        d.addCallback(self._on_append)
        d.addErrback(self._interrupt)

    def _append(self, *args):
        self.counter = 0
        try:
            for k, f in self.field_iterator.next():
                d = self.cb.get(k)
                d.addCallback(self._on_get, f)
                d.addErrback(self._interrupt)
        except StopIteration:
            logger.info('S0')
            reactor.stop()
            logger.info('S1')

    def append(self, host_port, bucket, password, iteration, r):
        logger.info('Running append iteration: {}-{}'.format(iteration, r))
        host, port = host_port.split(':')

        self.cb = Connection(bucket=bucket, host=host, password=password)
        d = self.cb.connect()
        d.addCallback(self._append)
        d.addErrback(self._interrupt)

        logger.info('S2')
        reactor.run()
        logger.info('Finished append iteration: {}-{}'.format(iteration, r))
