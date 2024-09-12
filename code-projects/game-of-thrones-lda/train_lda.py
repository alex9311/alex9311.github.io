import argparse
import boto3
import mxnet as mx
import nltk
import numpy as np
import os
import pickle
from sagemaker.amazon.common import numpy_to_record_serializer
from sagemaker.amazon.amazon_estimator import get_image_uri
import sagemaker
import tarfile

from helpers import import_documents_on_disk
from helpers import document_to_term_counts


def main():
    """
    example call
        python3 train_lda.py \
            --pageInputDir pages \
            --vocabFile vocab.pkl \
            --s3Bucket alex9311-sagemaker \
            --s3Prefix LDA-testing \
            --awsRole aws-sagemaker-execution-role
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('--vocabFile', action='store', required=True)
    parser.add_argument('--pageInputDir', action='store', required=True)
    parser.add_argument('--s3Bucket', action='store', required=True)
    parser.add_argument('--s3Prefix', action='store', required=True)
    args = parser.parse_args()

    bucket = args.s3Bucket
    prefix = args.s3Prefix
    role = args.awsRole

    vocab = pickle.load(open(args.vocabFile, 'rb'))
    documents = import_documents_on_disk(args.pageInputDir)
    for d in documents:
        d['term_counts'] = document_to_term_counts(d['tokens'], vocab)
    print('length of vocab: ', len(vocab))
    print('number of documents: ', len(documents))

    training_docs = np.array([d['term_counts'] for d in documents])

    # convert training_docs to Protobuf RecordIO format
    recordio_protobuf_serializer = numpy_to_record_serializer()
    training_docs_recordio = recordio_protobuf_serializer(training_docs)

    # upload to S3 in bucket/prefix/train
    fname = 'lda_training.data'
    s3_object = os.path.join(prefix, 'train', fname)
    boto3.Session().resource('s3').Bucket(bucket).Object(s3_object).upload_fileobj(training_docs_recordio)
    s3_train_data = 's3://{}/{}'.format(bucket, s3_object)
    print('Uploaded training data to S3: {}'.format(s3_train_data))

    region_name = boto3.Session().region_name
    container = get_image_uri(region_name, 'lda')

    print('Using SageMaker LDA container: {} ({})'.format(container, region_name))

    session = sagemaker.Session()

    print('Training input/output will be stored in {}/{}'.format(bucket, prefix))
    print('\nIAM Role: {}'.format(role))

    lda = sagemaker.estimator.Estimator(
        container,
        role,
        output_path='s3://{}/{}/output'.format(bucket, prefix),
        train_instance_count=1,
        train_instance_type='ml.m5.large',
        sagemaker_session=session,
    )

    # set algorithm-specific hyperparameters
    lda.set_hyperparameters(
        num_topics=10,
        feature_dim=len(vocab),
        mini_batch_size=len(documents),
        alpha0=1.0,
    )

    # run the training job on input data stored in S3
    lda.fit({'train': s3_train_data})

    training_job_name = lda.latest_training_job.job_name

    print('Training job name: {}'.format(training_job_name))

    model_fname = 'model.tar.gz'
    model_object = os.path.join(prefix, 'output', training_job_name, 'output', model_fname)
    boto3.Session().resource('s3').Bucket(bucket).Object(model_object).download_file(fname)
    with tarfile.open(fname) as tar:
        def is_within_directory(directory, target):
        	
        	abs_directory = os.path.abspath(directory)
        	abs_target = os.path.abspath(target)
        
        	prefix = os.path.commonprefix([abs_directory, abs_target])
        	
        	return prefix == abs_directory
        
        def safe_extract(tar, path=".", members=None, *, numeric_owner=False):
        
        	for member in tar.getmembers():
        		member_path = os.path.join(path, member.name)
        		if not is_within_directory(path, member_path):
        			raise Exception("Attempted Path Traversal in Tar File")
        
        	tar.extractall(path, members, numeric_owner=numeric_owner) 
        	
        
        safe_extract(tar)
    print('Downloaded and extracted model tarball: {}'.format(model_object))

    # obtain the model file
    model_list = [fname for fname in os.listdir('.') if fname.startswith('model_')]
    model_fname = model_list[0]
    print('Found model file: {}'.format(model_fname))

    # get the model from the model file and store in Numpy arrays
    alpha, beta = mx.ndarray.load(model_fname)
    learned_alpha_permuted = alpha.asnumpy()
    learned_beta_permuted = beta.asnumpy()

    topic_distributions = learned_beta_permuted.tolist()

    topic_word_weights_list = []
    for topic_distribution in topic_distributions:
        this_topic_word_weights = {}
        for word_index, weight in enumerate(topic_distribution):
            this_topic_word_weights[vocab[word_index]] = weight
        topic_word_weights_list.append(this_topic_word_weights)

    top_words_in_topics = []
    for topic_word_weights in topic_word_weights_list:
        top_words_in_topics.append(
            sorted(topic_word_weights, key=topic_word_weights.get, reverse=True)[:10]
        )
    for index, top_words_in_topic in enumerate(top_words_in_topics):
        print('topic', index)
        for word in top_words_in_topic:
            print('\t', word, ':', topic_word_weights_list[index][word])


if __name__ == '__main__':
    main()
