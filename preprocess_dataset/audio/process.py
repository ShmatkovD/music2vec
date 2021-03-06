import logging
import os
import numpy as np
from preprocess_dataset.audio.processors import get_processor

logger = logging.getLogger(__name__)


def get_audio_path(dataset_dir, dataset_size, track_id):
    tid_str = '{:06d}'.format(track_id)
    return os.path.join(dataset_dir, 'fma_' + dataset_size, tid_str[:3], tid_str + '.mp3')


def process_audio(dataset_dir, audio_metadata, proc_name):
    """
    :param dataset_dir: str
    :param audio_metadata: dict[int, dict]
    :param proc_name: str
    :return: dict[int, dict]
    """
    logger.info('Getting audio processor %s', proc_name)
    processor = get_processor(proc_name)

    for index, track_id in enumerate(audio_metadata.keys()):
        logger.info(
            'Processing audio %s, %s/%s',
            track_id, index,
            len(audio_metadata),
        )
        audio_path = get_audio_path(
            dataset_dir, audio_metadata[track_id]['subset'], track_id,
        )

        features = None
        for _ in range(3):
            try:
                features = processor(audio_path)
                break
            except Exception:
                pass

        if features is None:
            logger.warning('Audio has not been processed: %s', track_id)
            continue

        features = np.reshape(features, features.shape + (1,))  # to make it picture-like
        audio_metadata[track_id]['feature'] = features

    return audio_metadata
