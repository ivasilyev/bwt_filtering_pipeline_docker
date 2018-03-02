#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import sys
import argparse
import subprocess


def parse_args():
    starting_parser = argparse.ArgumentParser(description="This script performs two bowtie/bowtie2-based alignments. For the second alignment it takes the non-mapped reads. REFDATA files are generated by the 'cook_the_reference' script")
    starting_parser.add_argument("-f", "--filter", default=None,
                                 help="(Optional) (Not for single alignment) Filtering DNA sequence REFDATA")
    starting_parser.add_argument("-c", "--coverage", required=True,
                                 help="DNA sequence REFDATA to calculate coverage")
    starting_parser.add_argument("-s", "--sampledata", required=True,
                                 help="Input list containing two tab-delimited columns for colorspace or non-colorspace sequences and three for paired-end sequences: sample name and absolute path(s). May contain a header")
    starting_parser.add_argument("-m", "--mask", default="",
                                 help="(Optional) Mask to be added to resulting files. Automtically apended by both REFDATA file names")
    starting_parser.add_argument("-t", "--threads", default=None, type=int,
                                 help="(Optional) Number of CPU cores to use, maximal by default")
    starting_parser.add_argument("-n", "--no_coverage", default=False, action='store_true',
                                 help="(Optional) (Only for single alignment) If selected, cancels coverage extraction")
    starting_parser.add_argument("-o", "--output", required=True,
                                 help="Output directory")
    return starting_parser.parse_args()


def is_path_exists(path):
    try:
        os.makedirs(path)
    except OSError:
        pass


def ends_with_slash(string):
    if string.endswith("/"):
        return string
    else:
        return str(string + "/")


def file_append(string, file_to_append):
    file = open(file_to_append, 'a+')
    file.write(string)
    file.close()


def external_route(input_direction_list):
    process = subprocess.Popen(input_direction_list, shell=False, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (output, error) = process.communicate()
    process.wait()
    if error:
        print(error)
    return output.decode("utf-8")


def filename_only(string):
    return str(".".join(string.rsplit("/", 1)[-1].split(".")[:-1]))


def file_to_list(file):
    file_buffer = open(file, 'rU')
    output_list = [j for j in [re.sub('[\r\n]', '', i) for i in file_buffer] if len(j) > 0]
    file_buffer.close()
    return output_list


def find_latest_changed_file(mask):
    return subprocess.getoutput("ls -1t -d " + mask + " | head -1")


def parse_namespace():
    namespace = parse_args()
    for file_name in [namespace.coverage, namespace.sampledata]:
        if not os.path.isfile(file_name):
            raise ValueError("Not found: '" + file_name + "'\nIf you're using Docker, please make sure you have mounted required volume with the '-v' flag.")
    default_threads = int(subprocess.getoutput("nproc"))
    if not namespace.threads or default_threads < namespace.threads:
        namespace.threads = default_threads
    return namespace.filter, namespace.coverage, namespace.sampledata, namespace.mask, str(namespace.threads), namespace.no_coverage, namespace.output


if __name__ == '__main__':
    filteringGenomeRefData, coverageGenomeRefData, sampleDataFileName, inputMask, cpuThreadsString, noCoverageExtractionBool, outputDir = parse_namespace()
    scriptDir = ends_with_slash(os.path.dirname(os.path.realpath(sys.argv[0])))
    if filteringGenomeRefData:
        print("Filtering mapping for", sampleDataFileName, "on", filteringGenomeRefData)
        external_route(["python3", scriptDir + 'bowtie-tools/nBee.py', "-i", sampleDataFileName, "-r", filteringGenomeRefData, "-m", inputMask + '_' + filename_only(filteringGenomeRefData), "-t", cpuThreadsString, "-n", "-o", outputDir])
        filteredSampleDataFileName = re.sub('[\r\n]', '', find_latest_changed_file(outputDir + "Statistics/_non-mapped_reads_" + inputMask + "*.sampledata"))
        if len(filteredSampleDataFileName) == 0:
            raise ValueError("Only filtering alignment has been performed, but generated 'sampledata' could not be found!")
        print("Mapping and coverage extraction for", filteredSampleDataFileName, "on", coverageGenomeRefData)
        external_route(["python3", scriptDir + 'nBee.py', "-i", filteredSampleDataFileName, "-r", coverageGenomeRefData, "-m", "_".join([inputMask, 'no', filename_only(filteringGenomeRefData), filename_only(coverageGenomeRefData)]), "-t", cpuThreadsString, "-o", outputDir])
    else:
        print("Performing single alignment for", sampleDataFileName, "on", coverageGenomeRefData)
        cmd = ["python3", scriptDir + 'nBee.py', "-i", sampleDataFileName, "-r", coverageGenomeRefData, "-m", "_".join([inputMask, 'no', filename_only(filteringGenomeRefData), filename_only(coverageGenomeRefData)]), "-t", cpuThreadsString, "-o", outputDir]
        if noCoverageExtractionBool:
            cmd = cmd[:-2] + ["-n"] + cmd[-2:]
        external_route(cmd)
    print("Completed processing:", " ".join([i for i in sys.argv if len(i) > 0]))
