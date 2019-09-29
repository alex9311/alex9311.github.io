"""
script to read epub GOT books
creates text files representing pages stemmed words
"""
import os
import re
import argparse
import codecs
import ebooklib
from ebooklib import epub
import nltk
import pickle


def remove_stop_words(words, custom_stop_words=['said']):
    """given a list of single-word strings, removes stopwords
    """
    all_stopwords = set(nltk.corpus.stopwords.words('english')+custom_stop_words)
    return [word for word in words if word not in all_stopwords]


def stem(words):
    """given a list of single-word strings, uses PorterStemmer to stem
    """
    porter_stemmer = nltk.stem.PorterStemmer()
    return [porter_stemmer.stem(word) for word in words]


def remove_html_tags(doc):
    """given a html doc as a string, removes html elements
    """
    return re.sub('<.*?>', ' ', doc)


def remove_non_alpha(words):
    """given a list of single-word strings, removes non-alphanumeric words
    """
    return [word.lower() for word in words if word.isalpha()]


def remove_non_ascii(doc):
    """given a document, removes non-ascii words
    """
    return re.sub(r'[^\x00-\x7f]', r'', doc)


def tokenize(doc):
    """given a document, returns a list of single-word strings
    """
    return nltk.word_tokenize(doc.strip())


def count_words_in_documents(documents):
    word_counts = {}
    for document in documents:
        words_found_in_document = set()
        for word in document:
            if word not in word_counts:
                word_counts[word] = {'all_appearances': 1, 'document_appearances': 1}
            else:
                word_counts[word]['all_appearances'] += 1
                if word not in words_found_in_document:
                    word_counts[word]['document_appearances'] += 1
            words_found_in_document.add(word)
    return word_counts


def documents_to_vocab(documents, min_document_apperances, max_document_apperances):
    word_counts = count_words_in_documents(documents)
    vocab = word_counts_to_vocab(word_counts, min_document_apperances, max_document_apperances)

    return vocab


def word_counts_to_vocab(word_counts, min_document_apperances, max_document_apperances):
    vocab = []
    for word in word_counts:
        document_apperances = word_counts[word]['document_appearances']
        if document_apperances >= min_document_apperances and document_apperances <= max_document_apperances:
            vocab.append(word)
    return vocab


def raw_html_to_tokens(raw_doc):
    safe_doc = remove_non_ascii(remove_html_tags(raw_doc))
    raw_tokens = tokenize(safe_doc)
    processed_tokens = stem(remove_stop_words(remove_non_alpha(raw_tokens)))
    processed_tokens
    return [processed_token for processed_token in processed_tokens if len(processed_token) > 3]


def find_chapter_title_in_epub_item(item):
    # items are ebook sections
    if item.get_type() == ebooklib.ITEM_DOCUMENT:
        html_content = item.get_content().decode('utf-8')

        chapter_title_search = re.search(
            r'class="chapter(\d+)".*/>(.*)</h1>',
            html_content)
        if chapter_title_search is None:
            chapter_title_search = re.search(r'class="subchapter()".*strong>(.*)</strong>', html_content)
        if chapter_title_search is None:
            chapter_title_search = re.search(r'class="ct(\d?)">(.*)</p>', html_content)

        if chapter_title_search:
            chapter_title = remove_html_tags(chapter_title_search.groups(0)[1]).strip()
            return chapter_title
    return False


def book_to_tokens(book_file_path, pages_output_dir, words_per_page=250, write_processed_pages=True):
    """given a book_file_path, processes its contents and output text files
    of tokens
    """
    page_number = 0
    chapter_count = 0
    book = epub.read_epub(book_file_path)

    pages = []

    for item in book.get_items():
        # items are ebook sections
        chapter_title = find_chapter_title_in_epub_item(item)
        if chapter_title:
            chapter_count += 1

            raw_doc = item.get_body_content().decode('utf-8')
            processed_tokens = raw_html_to_tokens(raw_doc)

            processed_tokens_as_pages = [
                processed_tokens[i:i+words_per_page]
                for i in range(0, len(processed_tokens), words_per_page)
            ]
            processed_tokens_as_pages = [t for t in processed_tokens_as_pages if len(t) > words_per_page]

            if write_processed_pages:
                for tokens in processed_tokens_as_pages:
                    filename = pages_output_dir+'/'+chapter_title+'_'+str(page_number)+'.txt'
                    output_file = codecs.open(filename, 'w', 'utf-8')
                    output_file.write(' '.join(tokens))
                    output_file.close()
                    page_number = page_number + 1

            pages.extend(processed_tokens_as_pages)

    print('found ', chapter_count, ' chapters')
    print('created ', page_number, ' pages')
    return pages


def document_to_term_counts(document, vocab):
    term_count = [0] * len(vocab)
    for word in document:
        if word in vocab:
            term_count[vocab.index(word)] += 1
    return term_count


def import_documents_on_disk(directory_name):
    directory = os.fsencode(directory_name)
    documents = []

    count = 0
    for file in os.listdir(directory):
        filename = os.fsdecode(file)
        with open(os.path.join(directory_name, filename), 'r') as file:
            documents.append({
                'filename': filename,
                'chapter': filename.split('_')[0],
                'tokens': nltk.word_tokenize((file.read()))
            })

    return documents
