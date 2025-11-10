import os


class PathUtil(object):
    root_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    log_path = os.path.join(root_path, 'data/log')
    data_path = os.path.join(root_path, 'data')
    tmp_path = os.path.join(root_path, 'data/tmp')

    os.makedirs(log_path, exist_ok=True)
    os.makedirs(tmp_path, exist_ok=True)
