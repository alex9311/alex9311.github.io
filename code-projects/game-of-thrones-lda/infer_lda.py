import argparse
import csv
import pickle
import sagemaker
import os
from sagemaker.predictor import csv_serializer, json_deserializer
import numpy as np
import numpy as np
import operator

from helpers import import_documents_on_disk
from helpers import document_to_term_counts


def deploy_endpoint(training_job_name):
    lda = sagemaker.estimator.Estimator.attach(training_job_name)
    lda_inference = lda.deploy(
        initial_instance_count=1,
        instance_type='ml.m5.large',
    )

    lda_inference.content_type = 'text/csv'
    lda_inference.serializer = csv_serializer
    lda_inference.deserializer = json_deserializer

    return lda_inference


def chunker(seq, size):
    return (seq[pos:pos + size] for pos in range(0, len(seq), size))


def euclidean(v1, v2):
    return sum((p-q)**2 for p, q in zip(v1, v2)) ** .5


def main():
    """
    example call
        python3 infer_lda.py --pageInputDir pages \
            --vocabFile vocab.pkl \
            --trainingJobName your-lda-training-job-name
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('--vocabFile', action='store', required=True)
    parser.add_argument('--pageInputDir', action='store', required=True)
    parser.add_argument('--trainingJobName', action='store', required=True)
    parser.add_argument('--batchSize', default=100, action='store', type=int)

    args = parser.parse_args()

    vocab = pickle.load(open(args.vocabFile, 'rb'))
    documents = import_documents_on_disk(args.pageInputDir)
    documents = [d for d in documents if len(d['tokens']) >= 250]
    documents = pickle.load(open('documents.pkl', 'rb'))
    for d in documents:
        d['term_counts'] = document_to_term_counts(d['tokens'], vocab)

    training_job_name = args.trainingJobName
    lda_inference = deploy_endpoint(training_job_name)

    for doc_batch in chunker(documents, args.batchSize):
        print([d['filename'] for d in doc_batch])
        raw_batch_results = lda_inference.predict(np.array([d['term_counts'] for d in doc_batch]))
        for idx, prediction in enumerate(raw_batch_results['predictions']):
            doc_batch[idx]['topic_mixture'] = prediction['topic_mixture']

    with open('documents.pkl', 'wb') as f:
        pickle.dump(documents, f)

    sagemaker.Session().delete_endpoint(lda_inference.endpoint)

    documents = pickle.load(open('documents.pkl', 'rb'))

    edges = []
    for outer_loop_idx, vertice_1 in enumerate(documents):
        for vertice_2 in documents[(outer_loop_idx+1):]:
            distance = euclidean(vertice_1['topic_mixture'], vertice_2['topic_mixture'])
            edges.append({
                'vertice_1': vertice_1['filename'],
                'vertice_2': vertice_2['filename'],
                'euclidean_distance': distance,
                'weight': 1 - distance
            })

    desired_num_edges = round(len(documents)*(len(documents)-1)/500)
    edges.sort(key=operator.itemgetter('weight'), reverse=True)
    edges = edges[:desired_num_edges]

    with open('edges.csv', mode='w') as edges_file:
        edges_writer = csv.writer(edges_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        edges_writer.writerow(['source', 'target', 'weight', 'type'])
        for edge in edges:
            edges_writer.writerow([edge['vertice_1'], edge['vertice_2'], edge['weight'], 'undirected'])

    with open('vertices.csv', mode='w') as vertices_file:
        vertices_writer = csv.writer(vertices_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        vertices_writer.writerow(['id', 'label'])
        for document in documents:
            vertices_writer.writerow([document['filename'], document['chapter']])


if __name__ == '__main__':
    main()
