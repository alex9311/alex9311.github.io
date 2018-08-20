import sys
import urllib.request
import csv

if (len(sys.argv) < 2):
	print('firt arg is input file name')
	exit()

inputFile = sys.argv[1]
counter = 0

with open(inputFile, 'r') as csvfile:
	csvReader = csv.reader(csvfile)
	for row in csvReader:
		print(row)
		tweet = row[0].lower()
		if '#' in tweet or '@' in tweet:
			continue
		group = 'yes' if 'yes' in tweet else 'no'
		urllib.request.urlretrieve(row[1], 'data/'+group+'/'+group+'_'+str(counter)+'.jpg')
		counter = counter + 1
