import tensorflow as tf
import logging

logger = logging.getLogger(__name__)


FILTERS = 64


def build_simple_cnn(input, kernel_size):
    return tf.layers.conv2d(
        inputs=input,
        filters=FILTERS,
        kernel_size=kernel_size,
        padding='same',
        activation=tf.nn.relu,
    )


def build_kernel_model(input):
    with tf.variable_scope('kernel'):
        cnn1 = build_simple_cnn(input, [5, 5])
        cnn2 = build_simple_cnn(input, [3, 3])
        cnn3 = build_simple_cnn(input, [1, 1])

        pool1 = tf.layers.max_pooling2d(cnn1, pool_size=[2, 2], strides=2)
        pool2 = tf.layers.max_pooling2d(cnn2, pool_size=[2, 2], strides=2)
        pool3 = tf.layers.max_pooling2d(cnn3, pool_size=[2, 2], strides=2)

        flat1 = tf.contrib.layers.flatten(pool1)
        flat2 = tf.contrib.layers.flatten(pool2)
        flat3 = tf.contrib.layers.flatten(pool3)

        all_features = tf.concat([flat1, flat2, flat3], axis=1)

        result = tf.layers.dense(all_features, 200)

    return result


def build_simple_multilabel_loss(kernel_model, label, label_name):
    with tf.variable_scope('predictions/{}'.format(label_name)):
        pred = tf.layers.dense(
            inputs=kernel_model,
            units=label.shape[1],
            activation=tf.nn.relu,
        )
    with tf.variable_scope('losses/{}'.format(label_name)):
        loss = tf.nn.sigmoid_cross_entropy_with_logits(
            labels=label,
            logits=pred,
        )
        # to cast to scalar
        loss = tf.reduce_mean(tf.reduce_sum(loss, axis=1))
    with tf.variable_scope('accuracies/{}'.format(label_name)):
        acc = tf.metrics.accuracy(
            labels=tf.round(tf.nn.sigmoid(label)),
            predictions=pred,
        )
    summaries = [
        tf.summary.scalar('loss', loss),
        tf.summary.tensor_summary('accuracy', acc),
        tf.summary.tensor_summary('prediction', pred),
    ]
    return loss, acc, summaries


def build_simple_logit_loss(kernel_model, label, label_name):
    with tf.variable_scope('predictions/{}'.format(label_name)):
        pred = tf.layers.dense(inputs=kernel_model, units=1, activation=None)

    with tf.variable_scope('losses/{}'.format(label_name)):
        loss = tf.losses.mean_squared_error(
            labels=label,
            predictions=pred,
        )

    with tf.variable_scope('accuracies/{}'.format(label_name)):
        acc = tf.metrics.accuracy(
            labels=label,
            predictions=pred,
        )
    summaries = [
        tf.summary.scalar('loss', loss),
        tf.summary.tensor_summary('accuracy', acc),
        tf.summary.tensor_summary('prediction', pred),
    ]
    return loss, acc, summaries


def build_simple_cat_loss(kernel_model, label, label_name):
    with tf.variable_scope('predictions/{}'.format(label_name)):
        pred = tf.layers.dense(
            inputs=kernel_model,
            units=label.shape[1],
            activation=tf.nn.relu,
        )

    with tf.variable_scope('losses/{}'.format(label_name)):
        loss = tf.losses.softmax_cross_entropy(
            onehot_labels=label,
            logits=pred,
        )

    with tf.variable_scope('accuracies/{}'.format(label_name)):
        acc = tf.metrics.accuracy(
            labels=tf.argmax(label, axis=1),
            predictions=tf.argmax(pred, axis=1),
        )
    summaries = [
        tf.summary.scalar('loss', loss),
        tf.summary.tensor_summary('accuracy', acc),
        tf.summary.tensor_summary('prediction', pred),
    ]
    return loss, acc, summaries


METRICS = {
    # label, metric
    'genres_all': build_simple_multilabel_loss,
    'genres_top': build_simple_multilabel_loss,
    'release_decade': build_simple_cat_loss,
    'acousticness': build_simple_logit_loss,
    'danceability': build_simple_logit_loss,
    'energy': build_simple_logit_loss,
    'instrumentalness': build_simple_logit_loss,
    'speechiness': build_simple_logit_loss,
    'happiness': build_simple_logit_loss,
    'artist_location': build_simple_cat_loss,
}


def model_fn(features, labels, mode):
    with tf.variable_scope('model'):
        model = build_kernel_model(features['feature'])

        if mode == tf.estimator.ModeKeys.PREDICT:
            return tf.estimator.EstimatorSpec(
                mode,
                predictions=model
            )

        losses = []
        accs = {}
        summaries = []

        for label_name, metric in METRICS.items():
            if label_name not in labels:
                logger.warning('No label %s in labels', label_name)
                continue

            loss, acc, lsum = metric(model, labels[label_name], label_name)
            losses.append(loss)
            accs[label_name] = acc
            summaries.extend(lsum)

        with tf.variable_scope('losses/total'):
            total_loss = tf.math.reduce_sum(losses)
            summaries.append(
                tf.summary.scalar('total_loss', total_loss)
            )
            losses.append(total_loss)

        if mode == tf.estimator.ModeKeys.TRAIN:
            with tf.variable_scope('optimizer'):
                optimizer = tf.train.AdamOptimizer(
                    learning_rate=0.1,
                    epsilon=0.1,
                )
                # optimizer = tf.contrib.estimator.clip_gradients_by_norm(optimizer, 1)
                training_ops = [
                    optimizer.minimize(
                        loss=loss,
                        global_step=tf.train.get_global_step(),
                    )
                    for loss in losses
                ]

            summary_hook = tf.train.SummarySaverHook(
                1,
                output_dir='/tmp/music2vec_summary',
                summary_op=tf.summary.merge(summaries)
            )
            return tf.estimator.EstimatorSpec(
                mode=mode,
                loss=total_loss,
                train_op=tf.group(*training_ops),
                training_hooks=[summary_hook],
            )

        if tf.estimator.ModeKeys.EVAL:
            return tf.estimator.EstimatorSpec(
                mode=mode,
                loss=total_loss,
                eval_metric_ops=accs
            )
