import unittest
import gevent
import core

import logging
logging.basicConfig()
logger = logging.getLogger('tests')


class NumbersManagerTestCase(unittest.TestCase):

    def setUp(self):
        self.manager = core.NumbersManager()

    def test_init_state(self):
        self.assertEqual(0, len(self.manager.stashed_data))
        self.assertEqual(0, len(self.manager.aggregated))

    def test_aggregate_data(self):
        self.manager.aggregate_user_data('moe', 11)
        self.assertEqual(1, len(self.manager.aggregated))
        self.manager.aggregate_user_data('larry', 22)
        self.assertEqual(2, len(self.manager.aggregated))

    def test_aggregate_same_data(self):
        self.manager.aggregate_user_data('moe', 99)
        self.manager.aggregate_user_data('moe', 99)
        self.assertEqual(1, len(self.manager.aggregated))

    def test_get_data_packet_flushes_agg(self):
        self.manager.aggregate_user_data('moe', 11)
        self.manager.aggregate_user_data('larry', 22)
        self.manager.get_data_packet()
        self.assertEqual(0, len(self.manager.aggregated))

    def test_get_data_packet_adds_to_stash(self):
        self.manager.aggregate_user_data('moe', 11)
        self.manager.aggregate_user_data('larry', 22)
        self.manager.get_data_packet()
        self.assertTrue(2, len(self.manager.stashed_data))

    def test_get_data_packet_empty(self):
        packet = self.manager.get_data_packet()
        self.assertEqual(0, len(packet))

    def test_get_data_packet_single_entry(self):
        self.manager.aggregate_user_data('moe', 11)
        packet = self.manager.get_data_packet()
        self.assertEqual(1, len(packet))

    def test_get_data_packet_diff_entries(self):
        self.manager.aggregate_user_data('moe', 11)
        self.manager.aggregate_user_data('curly', 33)
        packet = self.manager.get_data_packet()
        self.assertEqual(2, len(packet))

    def test_get_data_packet_same_entry(self):
        self.manager.aggregate_user_data('moe', 11)
        self.manager.aggregate_user_data('moe', 22)
        packet = self.manager.get_data_packet()
        self.assertEqual(1, len(packet))

    def test_not_stashed_no_value_in_packet(self):
        self.manager.aggregate_user_data('moe', 11)
        # Since moe is not the stash it should have zero count in the packet
        packet = self.manager.get_data_packet()
        self.assertEqual(0, packet['moe'])

    def test_stashed_with_value_in_packet(self):
        self.manager.aggregate_user_data('moe', 11)
        self.manager.get_data_packet()
        logger.debug("stashed data in manager is: %s"
                     % self.manager.stashed_data)
        self.manager.aggregate_user_data('moe', 15)
        # Moe was stashed, it should have non-zero count in the packet
        packet = self.manager.get_data_packet()
        value = self.manager._compute(11, 15)
        logger.debug("packet is %s" % packet)
        self.assertEqual(value, packet['moe'])

    def test_compute_counts(self):
        self.assertEqual(5, self.manager._compute(10, 15))
        self.assertEqual(1, self.manager._compute(1, 2))

    def test_compute_with_zeros(self):
        self.assertEqual(0, self.manager._compute(0, 0))

    def test_compute_inverse_counts(self):
        self.assertEqual(0, self.manager._compute(15, 10))


###############################################################################

class NumbersPusherTestCase(unittest.TestCase):

    def setUp(self):
        mon = core.NumbersManager()
        self.pusher = core.NumbersPusher(mon, 1)

    def test_not_running(self):
        self.assertFalse(self.pusher.running)

    def test_stop_when_not_running(self):
        self.pusher.stop()
        self.assertFalse(self.pusher.running)

    def test_start_stop(self):
        gevent.spawn(self.pusher.start)
        gevent.sleep()
        self.assertTrue(self.pusher.running)
        self.pusher.stop()
        gevent.sleep()
        self.assertFalse(self.pusher.running)

    def test_push_packet(self):
        self.pusher.manager.aggregate_user_data('moe', 11)
        packet = self.pusher.manager.get_data_packet()
        self.pusher._push(packet)
        self.assertEqual(1, len(self.pusher._pusher.pushed))
        self.assertEqual(packet, self.pusher._pusher.pushed[0])

    def test_push_empty_packet(self):
        packet = self.pusher.manager.get_data_packet()
        self.pusher._push(packet)
        self.assertEqual(1, len(self.pusher._pusher.pushed))
        self.assertEqual(packet, self.pusher._pusher.pushed[0])
