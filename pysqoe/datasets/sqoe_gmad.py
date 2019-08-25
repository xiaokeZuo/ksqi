import os
import pandas as pd
from pysqoe.datasets import StreamingDatabase
from pysqoe.utils import download, extract


class SQoEgMAD(StreamingDatabase):
    # feature: extracted features and mos
    # server_video: extracted features, encoded representations, dash videos, and mos
    # full: extracted features, encoded representations, dash videos, streaming videos, and mos
    __valid_versions = ['feature', 'server_video']

    def __init__(self, root_dir, version='feature', download=True):
        if download:
            self._download(root_dir=root_dir, version=version)

        self.name = 'SQoE-gMAD'
        csv_file = os.path.join(root_dir, 'data.csv')
        streaming_log_dir = os.path.join(root_dir, 'streaming_logs')
        video_element_dir = os.path.join(root_dir, 'server_videos') \
                                if version != 'feature' else None
        feature_profile_dir = os.path.join(root_dir, 'feature_profiles') \
                                if version != 'feature' else None
        super().__init__(csv_file=csv_file,
                         streaming_log_dir=streaming_log_dir,
                         video_element_dir=video_element_dir,
                         feature_profile_dir=feature_profile_dir)

    def _download(self, root_dir, version='feature'):
        assert version in self.__valid_versions
        if not os.path.isdir(root_dir):
            os.makedirs(root_dir)
        elif os.path.isfile(os.path.join(root_dir, 'data.csv')):
            df = pd.read_csv(os.path.join(root_dir, 'data.csv'))
            streaming_logs = df.to_dict(orient='list')
            if all([os.path.isfile(os.path.join(root_dir, 'streaming_logs', s))
                    for s in streaming_logs['streaming_log']]):
                print('SQoE-gMAD already downloaded.')
                return
        
        url = 'https://ivc.uwaterloo.ca/database/SQoE-gMAD/'
        if version == 'feature':
            filename = 'sqoe_gmad_feature.zip'
            url += filename
        else:
            filename = 'sqoe_gmad_server_video.zip'
            url += filename

        zip_filename = os.path.join(root_dir, filename)
        if not os.path.isfile(zip_filename):
            print('Downloading SQoE-gMAD database...\n')
            download(url, zip_filename)
            print('SQoE-gMAD database download complete!\n')
        
        # extract zip
        extract(zip_filename, root_dir)
