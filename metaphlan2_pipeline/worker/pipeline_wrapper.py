#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import sys
import argparse
import subprocess


def parse_args():
    starting_parser = argparse.ArgumentParser(description="This script performs bowtie/bowtie2-based alignment and processes the output using MetaPhlAn 2. REFDATA files are generated by the 'cook_the_reference' script")
    starting_parser.add_argument("-r", "--refdata", required=True,
                                 help="Referent DNA sequence REFDATA")
    starting_parser.add_argument("-s", "--sampledata", required=True,
                                 help="Input list containing two tab-delimited columns for colorspace or non-colorspace sequences and three for paired-end sequences: sample name and absolute path(s). May contain a header")
    starting_parser.add_argument("-m", "--mask", default="",
                                 help="(Optional) Mask to be added to resulting files. Automtically apended by both REFDATA file names")
    starting_parser.add_argument("-t", "--threads", default=None, type=int,
                                 help="(Optional) Number of CPU cores to use, maximal by default")
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


def external_route(input_direction_list, output_direction):
    process = subprocess.Popen(input_direction_list, shell=False, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (output, error) = process.communicate()
    process.wait()
    if error:
        print(error)
    if not output_direction:
        return output.decode("utf-8").replace('\r', '').replace('\n', '')
    else:
        file_append(output.decode("utf-8"), output_direction)


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
    if not os.path.isfile(namespace.refdata):
        raise ValueError("Not found: '" + namespace.refdata + "'\nIf you're using Docker, please make sure you have mounted required volume with the '-v' flag.")
    default_threads = int(subprocess.getoutput("nproc"))
    if not namespace.threads or default_threads < namespace.threads:
        namespace.threads = default_threads
    namespace.output = ends_with_slash(namespace.output)
    return namespace.refdata, namespace.sampledata, namespace.mask, str(namespace.threads), namespace.output


def run_metaphlan2(mapped_sampledata_file):
    output_dir = ends_with_slash(outputDir) + "metaphlan2/"
    is_path_exists(output_dir)
    merging_files_names_list = []
    for i in file_to_list(mapped_sampledata_file):
        try:
            sample_name, sam_file_path = i.split("\t")
        except ValueError:
            raise ValueError("Not found: " + i)
        output_file_name = output_dir + sample_name + "_" + inputMask + ".mpa2"
        external_route(["python", scriptDir + "metaphlan2/metaphlan2.py", sam_file_path, "--input_type", "sam", "--nproc", cpuThreadsString],
                       output_file_name)
        merging_files_names_list.append(output_file_name)
    external_route(["python", scriptDir + "metaphlan2/utils/merge_metaphlan_tables.py", " ".join(merging_files_names_list)],
                   output_dir + filename_only(mapped_sampledata_file) + ".mpa2")
    print("Completed processing mapped file:", mapped_sampledata_file)


if __name__ == '__main__':
    refDataFileName, sampleDataFileName, inputMask, cpuThreadsString, outputDir = parse_namespace()
    scriptDir = ends_with_slash(os.path.dirname(os.path.realpath(sys.argv[0])))
    if not all(os.path.isfile(i) for i in [scriptDir + "metaphlan2/metaphlan2.py", scriptDir + "metaphlan2/utils/merge_metaphlan_tables.py"]):
        raise ValueError("MetaPhlAn2 scripts were not found! \nPlease clone the repository using the command: 'cd " + scriptDir + "; hg clone https://bitbucket.org/biobakery/metaphlan2'")
    print("Performing single alignment for", sampleDataFileName, "on", refDataFileName)
    external_route(["python3", scriptDir + 'nBee.py', "-i", sampleDataFileName, "-r", refDataFileName, "-m", inputMask, "-t", cpuThreadsString, "-o", outputDir], None)
    print("Completed processing:", " ".join([i for i in sys.argv if len(i) > 0]))
    mappedSampleDataFileName = re.sub('[\r\n]', '', find_latest_changed_file(outputDir + "Statistics/_mapped_reads_" + inputMask + "*.sampledata"))
    if len(mappedSampleDataFileName) == 0:
        raise ValueError("Only filtering alignment has been performed, but generated 'sampledata' could not be found!")
    print("Launching MetaPhlAn2 to process", mappedSampleDataFileName)
    run_metaphlan2(mappedSampleDataFileName)