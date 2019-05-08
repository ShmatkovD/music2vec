import logging
import os
import sys
import tensorflow as tf
from common.dataset_records import FeaturedRecord
from model.model import model_fn
tf.enable_eager_execution()

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)


def prepare_dataset(ds_path):
    dataset = tf.data.TFRecordDataset(
        ds_path
    ).map(
        FeaturedRecord.parse
    ).map(
        FeaturedRecord.split_features_labels
    ).shuffle(
        1000, 54321, reshuffle_each_iteration=True
    ).batch(
        100
    ).prefetch(
        100
    )
    return dataset.make_one_shot_iterator()


def parse_args(parser):
    parser.add_argument('--dataset', help='Path to dataset')
    args = parser.parse_args()
    return args


def main(dataset):
    logger.info('Start')
    estimator = tf.estimator.Estimator(
        model_fn=model_fn,
        config=tf.estimator.RunConfig(
            save_checkpoints_steps=20,
            model_dir='/tmp/music2vec_models',
        )
    )

    logger.info('Load dataset')
    train_path = os.path.join(dataset, 'train.tfrecord')
    test_path = os.path.join(dataset, 'test.tfrecord')

    logger.info('Train')
    estimator.train(
        input_fn=lambda: prepare_dataset(train_path).get_next(),
        steps=5
    )

    logger.info('Test')
    e = estimator.evaluate(lambda: prepare_dataset(test_path))
    print("Testing Accuracy:", e['accuracy'])
