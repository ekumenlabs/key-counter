from gevent import monkey
monkey.patch_all()

import unittest
import gevent
import core
import config

import logging
logging.basicConfig()
logger = logging.getLogger('integration')


class Integration (unittest.TestCase):

    # Test data manager, pusher and configuration manager for a single upstream
    # pushing to RAM.
    def test_single(self):
        upstreams = [{
            "name": "testing",
            "type": "test",
            "options": {"dummy_option": "1"}
        }]

        logger.info("booting objects.")
        data_manager = core.NumbersManager()
        pusher = core.NumbersPusher(data_manager, interval=0.1)
        self.config = config.ConfigManager(pusher, config=upstreams)

        push_stack = pusher._pushers["testing"].pushed

        # The pusher has been created.
        self.assertEqual(1, len(self.config._config))
        self.assertTrue("testing" in pusher._pushers)
        self.assertEqual(pusher._pushers["testing"].dummy_option, "1")

        # Aggregate some data and check it's been pushed.
        logger.info("aggregating data.")
        data_manager.aggregate_user_data("test user", 19)
        self.assertEqual(0, len(push_stack))
        logger.info("pushing collected data.")
        packet = data_manager.get_data_packet()
        pusher._push(packet)
        gevent.sleep(0.3)
        self.assertEqual(1, len(push_stack))

    # Test data manager, pusher and configuration manager for two upstreams
    # pushing to RAM.
    def test_dual(self):
        upstreams = [{
            "name": "one",
            "type": "test",
            "options": {"dummy_option": "1"}
        }, {
            "name": "two",
            "type": "test"
        }]

        logger.info("booting objects.")
        data_manager = core.NumbersManager()
        pusher = core.NumbersPusher(data_manager, interval=0.1)
        self.config = config.ConfigManager(pusher, config=upstreams)

        one_push_stack = pusher._pushers["one"].pushed
        two_push_stack = pusher._pushers["two"].pushed

        # The upstreams has been created.
        self.assertEqual(2, len(self.config._config))
        self.assertTrue("one" in pusher._pushers)
        self.assertTrue("two" in pusher._pushers)
        self.assertEqual(pusher._pushers["one"].dummy_option, "1")

        # Aggregate some data and check it's been pushed.
        logger.info("aggregating data.")
        data_manager.aggregate_user_data("test user", 19)
        self.assertEqual(0, len(one_push_stack))
        self.assertEqual(0, len(two_push_stack))
        logger.info("pushing collected data.")
        packet = data_manager.get_data_packet()
        pusher._push(packet)
        gevent.sleep(0.3)
        self.assertEqual(1, len(one_push_stack))
        self.assertEqual(1, len(two_push_stack))
