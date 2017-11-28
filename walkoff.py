import logging.config
import sys
import traceback
import os
from os.path import isfile
from core.config import config, paths
from apps import *
from gevent import monkey
from gevent import pywsgi

logger = logging.getLogger('walkoff')


def setup_logger():
    log_config = None
    if isfile(paths.logging_config_path):
        try:
            with open(paths.logging_config_path, 'rt') as log_config_file:
                log_config = json.loads(log_config_file.read())
        except:
            print('Invalid JSON in logging config file')
            pass
    else:
        print('No logging config found')

    if log_config is not None:
        logging.config.dictConfig(log_config)
    else:
        logging.basicConfig()
        logger.info("Basic logging is being used")


def run():
    from core.multiprocessedexecutor.multiprocessedexecutor import spawn_worker_processes
    setup_logger()
    pids = spawn_worker_processes()
    monkey.patch_all()
    from server import flaskserver
    flaskserver.running_context.controller.initialize_threading(pids=pids)
    # The order of these imports matter for initialization (should probably be fixed)
    from compose_api import compose_api
    compose_api()

    import core.case.database as case_database
    case_database.initialize()

    try:
        port = int(config.port)
    except ValueError:
        print('Invalid port {0}. Port must be an integer'.format(config.port))
    else:
        host = config.host
        if isfile(paths.certificate_path) and isfile(paths.private_key_path):
            server = pywsgi.WSGIServer((host, port), application=flaskserver.app,
                                       keyfile=paths.private_key_path, certfile=paths.certificate_path)
            proto = 'https'
        else:
            server = pywsgi.WSGIServer((host, port), application=flaskserver.app)
            proto = 'http'
        from core.config.config import walkoff_version
        logger.info('*** Running WALKOFF v.{} ***'.format(walkoff_version))
        logger.info('Listening on host {0}://{1}:{2}'.format(proto, host, port))

        server.serve_forever()


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        logger.info('Caught KeyboardInterrupt!')
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_exc()
    finally:
        from server import flaskserver

        flaskserver.running_context.controller.shutdown_pool()
        logger.info('Shutting down server')
        os._exit(0)
