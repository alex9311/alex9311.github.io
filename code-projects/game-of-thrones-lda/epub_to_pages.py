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
import pickle

from helpers import raw_html_to_tokens
from helpers import find_chapter_title_in_epub_item
from helpers import documents_to_vocab


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
                processed_tokens[i:i+250]
                for i in range(0, len(processed_tokens), words_per_page)
            ]

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


def main():
    """
    example call
        python3 epub_to_pages.py --booksInputDir books --pagesOutputDir pages --vocabOutputFile vocab.pkl
    where books contains epub files
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('--booksInputDir', action='store', required=True)
    parser.add_argument('--pagesOutputDir', action='store', required=True)
    parser.add_argument('--vocabOutputFile', action='store', required=True)
    args = parser.parse_args()

    if not os.path.exists(args.pagesOutputDir):
        os.makedirs(args.pagesOutputDir)

    pages = []
    books = [args.booksInputDir+'/'+book for book in os.listdir(args.booksInputDir) if '.epub' in book]
    for book in books:
        print('processing book '+book)
        pages.extend(book_to_tokens(book, args.pagesOutputDir))

    vocab = documents_to_vocab(pages, min_document_apperances=15, max_document_apperances=len(pages)/2)

    print('extracted a vocab of size', len(vocab))

    with open(args.vocabOutputFile, 'wb') as f:
        pickle.dump(vocab, f)


if __name__ == '__main__':
    main()
