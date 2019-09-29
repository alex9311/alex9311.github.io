Preprocess epub files into a vocab and documents with:
```bash
python3 epub_to_pages.py --booksInputDir books --pagesOutputDir pages --vocabOutputFile vocab.pkl
```

Then train your model with the data with:
```bash
python3 train_lda.py \
    --pageInputDir pages \
    --vocabFile vocab.pkl \
    --s3Bucket alex9311-sagemaker \
    --s3Prefix LDA-testing \
    --awsRole aws-sagemaker-execution-role
```

Then used the trained model for inference with
```bash
python3 infer_lda.py --pageInputDir pages \
    --vocabFile vocab.pkl \
    --trainingJobName your-lda-training-job-name
```
