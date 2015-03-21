#!/usr/bin/python

from __future__ import print_function

import argparse
import os
import sys

import sqlite3

import math

def printable(symbol):
	if (not symbol):
		return symbol

	if (ord(symbol) >= ord("!") and ord(symbol) <= ord("~")):
		return symbol
	else:
		return "0x" + symbol.encode("hex")


def entropy(input, verbose):
	# Dictionary of dictionaries used to store the frequency of each
	# symbol at each offset from the beginning of an input token.
	frequency = {}

	token_count = 0

	# Count the frequency of each character at each offset within a token.
	for token in input:
		verbose and print("<\t%s" % token, file=sys.stderr)
		token_count += 1

		for index in range(0, len(token)):
			symbol = token[index]
			if (not index in frequency):
				frequency[index] = {}
			if (not symbol in frequency[index]):
				frequency[index][symbol]  = 1
			else:
				frequency[index][symbol] += 1

	# Some tokens might be shorter than others. We assume that shorter tokens
	# are padded to the length of the longest token using symbol None. This
	# makes sure that the sum of the symbol frequencies at each index equals
	# the number of entries we have processed. In terms of entropy calculation
	# this factors in the length of the entries.
	for index in sorted(frequency.keys(), reverse=True):
		frequency_sum = token_count

		for symbol in frequency[index].keys():
			frequency_sum -= frequency[index][symbol]
		assert (frequency_sum >= 0),\
			"frequency_sum[%d] %d < 0" % (index, frequency_sum)

		if (frequency_sum == 0):
			break

		frequency[index][None] = frequency_sum

	# Dictionary used to store the sum of symbol frequencies
	# at each offset from the beginning of a token.
	# Should be equal to number of tokens (see above).
	frequency_sums = {}

	# Dictionary of dictionaries used to store the probability
	# of each symbol at each offset from the beginning of a token.
	probability = {}

	for index in frequency.keys():
		# Assertion: sum up the frequencies of all symbols at each index.
		# They must be equal to the number of entries processed, i.e., every
		# entry must have at least one symbol (even None, see above) at every
		# index.
		if (not index in frequency_sums):
			frequency_sums[index] = 0
			for symbol in frequency[index].keys():
				frequency_sums[index] += frequency[index][symbol]
			assert (frequency_sums[index] == token_count)
		#
		for symbol in frequency[index].keys():
			if (not index in probability):
				probability[index] = {}
			probability[index][symbol] =\
				float(frequency[index][symbol]) / frequency_sums[index]

	# Assertion: individual probabilities at each index must sum up to 1
	for index in frequency.keys():
		probability_sum = 0
		for symbol in frequency[index].keys():
			probability_sum += probability[index][symbol]
		# 0.999 and above get rounded up to 1.0
		assert (int(probability_sum+0.001) == 1),\
			"probability_sum[%d] (%.100f) %d != 1" %\
				(index, probability_sum, int(probability_sum+0.001))

	# Shannon Entropy
	for token in input:
		entropy = 0

		for index in frequency.keys():
			if (index < len(token)):
				symbol = token[index]
			else:
				symbol = None

			entropy += probability[index][symbol] *\
				math.log(probability[index][symbol], 2)

			verbose and print(">\t%s\t[%d] P(%s) = %f F(%s) = %d / %d E[0:%d] = %f" %
				(token, index, printable(symbol), probability[index][symbol],
				printable(symbol), frequency[index][symbol], frequency_sums[index],
				index + 1, 0 - entropy), file=sys.stderr)

		entropy = 0 - entropy

		print("%s\t%f" % (token, entropy))


# Input file is expected to be either:
# a) a set of entries on individual tokens
# b) a cookies.sqlite database maintained by Firefox (moz_cookies table)
#
# Output is an equivalent number of tokens with tab-separated values
# where the left value is the original entry and the right value is
# the calculated entropy in bits.

def main(argv):

	parser = argparse.ArgumentParser(description=
		"Calculate entropy given a set of values" +
			"or a cookies.sqlite Firefox database.")

	parser.add_argument("--verbose", "-v",
		action="store_const", const=True, default=False,
		help="output details on how entropy is calculated")

	parser.add_argument("input", nargs=1,
		help="name of the input file (e.g., cookie_values.txt or cookies.sqlite")

	args = parser.parse_args()

	root, ext = os.path.splitext(args.input[0])
	if (ext == ".sqlite"):
		conn = sqlite3.connect(args.input[0]) or die()
		c = conn.cursor()
		c.execute("SELECT value FROM moz_cookies")
		entropy(
			map(lambda x: x[0].encode('utf-8', errors='strict') ,c.fetchall()),
			args.verbose)
		conn.close()
	else:
		args.verbose and print("# NOTICE: Treating '%s' as a text file" %
				(args.input[0]), file=sys.stderr)
		file = open(args.input[0], "r") or die()
		entropy(map(lambda x: x.strip("\n"), file.readlines()), args.verbose)
		file.close()


if __name__ == "__main__":
	main(sys.argv)
