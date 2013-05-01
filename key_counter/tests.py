import unittest
import json
import gevent
import core
import config

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
        self.pusher.add_upstream('tests', strategy="test")

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
        self.assertEqual(1, len(self.pusher._pushers['tests'].pushed))
        self.assertEqual(packet, self.pusher._pushers['tests'].pushed[0])

    def test_push_empty_packet(self):
        packet = self.pusher.manager.get_data_packet()
        self.pusher._push(packet)
        self.assertEqual(1, len(self.pusher._pushers['tests'].pushed))
        self.assertEqual(packet, self.pusher._pushers['tests'].pushed[0])

    def test_remove_last_upstream(self):
        self.pusher.remove_upstream("tests")
        self.assertEqual({}, self.pusher._pushers)

    def test_add_another_upstream(self):
        self.pusher.add_upstream("tests second", "test")
        they_are_there = ("tests" in self.pusher._pushers
                          and "tests second" in self.pusher._pushers)
        self.assertTrue(they_are_there)

    def test_add_and_remove(self):
        orig = self.pusher._pushers.copy()
        self.pusher.add_upstream("another test", "test")
        self.pusher.remove_upstream("another test")
        self.assertItemsEqual(orig, self.pusher._pushers)

    def test_swap_upstreams(self):
        self.pusher.add_upstream("new tests", "test")
        self.pusher.remove_upstream("tests")
        swaped = ("tests" not in self.pusher._pushers
                  and "new tests" in self.pusher._pushers)
        self.assertTrue(swaped)


###############################################################################

class ConfigManagerTestCase (unittest.TestCase):

    def setUp(self):
        manager = core.NumbersManager()
        pusher = core.NumbersPusher(manager, 1)
        self.c = config.ConfigManager(pusher)

    def test_empty_config(self):
        config = []
        self.c.reconfigure(config)

    def test_simple_reconfigure(self):
        config = [{
            "name": "testing",
            "type": "test"
        }]
        self.c.reconfigure(config)

    def test_simple_with_options(self):
        config = [{
            "name": "testing",
            "type": "test",
            "options": {}
        }]
        self.c.reconfigure(config)

    def test_bad_config(self):
        config = [{
            "name": "testing",
        }]
        self.assertRaises(ValueError, self.c.reconfigure, config)
        config = [{
            "type": "testing",
        }]
        self.assertRaises(ValueError, self.c.reconfigure, config)

    def test_configured_upstream(self):
        config = [{
            "name": "testing",
            "type": "test"
        }]
        self.c.reconfigure(config)
        self.assertTrue("testing" in self.c.pusher._pushers)

    def test_configured_multiple_upstream(self):
        config = [{
            "name": "testing",
            "type": "test"
        }, {
            "name": "second testing",
            "type": "test"
        }]
        self.c.reconfigure(config)
        self.assertTrue("testing" in self.c.pusher._pushers)
        self.assertTrue("second testing" in self.c.pusher._pushers)

    def test_remove_upstream(self):
        config = [{
            "name": "testing",
            "type": "test"
        }, {
            "name": "second testing",
            "type": "test"
        }]
        self.c.reconfigure(config)
        self.assertTrue("testing" in self.c.pusher._pushers)
        self.assertTrue("second testing" in self.c.pusher._pushers)
        first = self.c._config["second testing"]
        config = [{
            "name": "second testing",
            "type": "test"
        }]
        self.c.reconfigure(config)
        self.assertTrue("testing" not in self.c.pusher._pushers)
        self.assertTrue("second testing" in self.c.pusher._pushers)
        second = self.c._config["second testing"]
        self.assertEqual(id(first), id(second))

    def test_add_upstream(self):
        config = [{
            "name": "second testing",
            "type": "test"
        }]
        self.c.reconfigure(config)
        first = self.c._config["second testing"]
        config = [{
            "name": "testing",
            "type": "test"
        }, {
            "name": "second testing",
            "type": "test"
        }]
        self.c.reconfigure(config)
        self.assertTrue("testing" in self.c.pusher._pushers)
        self.assertTrue("second testing" in self.c.pusher._pushers)
        second = self.c._config["second testing"]
        self.assertEqual(id(first), id(second))

    def test_modify_upstream(self):
        config = [{
            "name": "testing",
            "type": "test",
        }, {
            "name": "second testing",
            "type": "test"
        }]
        self.c.reconfigure(config)
        first = id(self.c._config["second testing"])

        # Same configuration, but add an option to "testing" upstream
        config = [{
            "name": "testing",
            "type": "test",
            "options": {"dummy_option": "1"}
        }, {
            "name": "second testing",
            "type": "test"
        }]
        self.c.reconfigure(config)

        # Ensure the other upstream is not affected.
        second = id(self.c._config["second testing"])

        self.assertEqual(first, second)
        testing_pusher = self.c.pusher._pushers["testing"]
        self.assertTrue(hasattr(testing_pusher, 'dummy_option'))
        self.assertEqual("1", testing_pusher.dummy_option)


class ConfigFileManagerTestCase (unittest.TestCase):

    FILE = 'test-config.json'

    def setUp(self):
        manager = core.NumbersManager()
        pusher = core.NumbersPusher(manager, 1)
        self.c = config.ConfigManager(pusher)

        with open(self.FILE, 'w') as f:
            json.dump([], f)

    def tearDown(self):
        import os
        os.remove(self.FILE)

    def test_simplest_config(self):
        cmanager = config.ConfigFileManager(
            self.c, self.FILE, interval=0)

        self.assertEqual(0, len(self.c._config))
        # The simplest possible configuration.
        with open(self.FILE, 'w') as f:
            f.write('[]')
        # Give opportunity to discover the config.
        gevent.sleep()
        self.assertEqual(0, len(cmanager.config_manager._config))

    def test_config(self):
        cmanager = config.ConfigFileManager(
            self.c, self.FILE, interval=0)

        self.assertEqual(0, len(self.c._config))
        conf = {
            "name": "testing",
            "type": "test"
        }
        with open(self.FILE, 'w') as f:
            json.dump([conf], f)
        # Give opportunity to discover the config.
        gevent.sleep(1)
        self.assertTrue("testing" in cmanager.config_manager._config)
