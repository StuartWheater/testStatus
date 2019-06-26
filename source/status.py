#! /usr/bin/env python3

# Build a testing status web page. Based on:
#   1) What functions exist in the R folder of the local repo.
#   2) What test files exist in the testhtat folder in the local repo.
#   3) Output of devtools::test().

# The list of functions in the R folder is the canonical list this script uses.

# Using the junit output of devtools::test
# options(testthat.output_file = "somefile")
# devtools::test('/home/vagrant/dsdev/dsbetatestclient', reporter = "junit")

# Drive everything from the context specified in the testthat scripts.
# The pre-defined format of these is:
# <function name>()::<test type>::<Optional other info>
# someFunction()::smoke::extra information.

# To do:
# - pass in repo and branch name as arguements

import argparse
import datetime
import csv
import glob
import os.path
import pprint
import sys
import xml.etree.ElementTree as ET

__author__ = "Olly Butters"
__date__ = 26/6/19


################################################################################
# Calculate the pass rate of this function and test class, then make a HTML
# table cell out of it. If there are errors put them in the cell.
def calculate_pass_rate(ds_test_status, function_name, test_class, gh_log_url):
    try:
        this_skipped = int(ds_test_status[function_name][test_class]['skipped'])
        this_failures = int(ds_test_status[function_name][test_class]['failures'])
        this_errors = int(ds_test_status[function_name][test_class]['errors'])
        this_number = int(ds_test_status[function_name][test_class]['number'])

        this_problems = this_skipped + this_failures + this_errors

        if this_problems == 0:
            return('<td class="good"><a href ="' + gh_log_url + '" target="_blank">' + str(this_number) + "/" + str(this_number) + "</a></td>")
        elif this_problems > 0:
            return('<td class="bad"><span class="tooltip"><a href ="' + gh_log_url + '" target="_blank">' + str(this_number - this_problems) + "/" + str(this_number) + '</a><span class="tooltiptext">' + '<br/>----------<br/>'.join(map(str, ds_test_status[function_name][test_class]['failureText'])) + '</span></span></td>')
    except:
        return("<td></td>")


################################################################################
# Parse the coverage file, returning a dict of file coverages
def parse_coverage(coverage_file_path):
    input_file = csv.reader(open(coverage_file_path))
    coverage = {}
    for row in input_file:
        print(row)
        this_function_name = row[0].replace("R/","")
        this_function_name = this_function_name.replace(".R","")
        coverage[this_function_name] = row[1]

    return coverage

################################################################################
#
def main(args):
    remote_root_path = "http://github.com/datashield/"
    repo_name = "dsBetaTestClient"
    branch_name = "master"

    parser = argparse.ArgumentParser()
    parser.add_argument("log_file_path", help="Path to the log file.")
    parser.add_argument("coverage_file_path", help="Path to the coverage file.")
    parser.add_argument("output_file_path", help="Path to the output file.")
    parser.add_argument("local_repo_path", help="Path to the locally checked out repository.")
    args = parser.parse_args()
    devtools_test_output_file = args.log_file_path
    coverage_file_path = args.coverage_file_path
    output_file_name = args.output_file_path
    local_repo_path = args.local_repo_path

    pp = pprint.PrettyPrinter(indent=4)

    remote_repo_path = remote_root_path + repo_name

    log_file = os.path.basename(devtools_test_output_file)
    gh_log_url = 'https://github.com/datashield/testStatus/blob/master/logs/' + log_file

    # Check repo exists
    print("local repo path: " + local_repo_path)
    print("remote repo path: " + remote_repo_path)

    ################################################################################
    # Get list of functions from R folder in the local repo
    #
    print("\n\n##########")
    ds_functions_path = glob.glob(local_repo_path + "/R/*.R")

    print("Number of local functions found: " + str(len(ds_functions_path)))

    ds_functions = []
    for this_path in ds_functions_path:
        ds_functions.append(os.path.basename(this_path))

    ds_functions.sort()

    for this_function in ds_functions:
        print(this_function)

    # Make the test status dictionary
    ds_test_status = {}
    for this_function in ds_functions:
        this_function = this_function.replace('.R', '')  # Drop the .R part from the end.
        ds_test_status[this_function] = {}

    ################################################################################
    # Get the list of tests from the local repo
    print("\n\n##########")
    ds_tests_path = glob.glob(local_repo_path + "/tests/testthat/*.R")

    print("Number of local test files found: " + str(len(ds_tests_path)))

    ds_tests = []
    for this_test in ds_tests_path:
        ds_tests.append(os.path.basename(this_test))

    # Drop the before and after scripts
    ds_tests.remove('setup.R')
    ds_tests.remove('teardown.R')

    ds_tests.sort()

    for this_test in ds_tests:
        print(this_test)

    ################################################################################
    # Parse the devtools::tests() log file, this is the output of the testthat tests
    #
    print("\n\n##########")

    print("Parsing XML file: " + devtools_test_output_file)

    tree = ET.parse(devtools_test_output_file)
    root = tree.getroot()

    print(root.tag)

    # Cycle through the xml line by line. This will have data for ALL tests.
    # The 'context' in testthat is the 'name' in the xml file.
    # The expected format of the context is:
    # <function name>::<maths|expt|smk|args|disc>::<Optional other info>::<single|multiple>
    # e.g.
    # ds.asFactor.o::smoke
    for testsuite in root:
        print('\n', testsuite.attrib['name'], testsuite.attrib['tests'], testsuite.attrib['skipped'], testsuite.attrib['failures'], testsuite.attrib['errors'])

        context = testsuite.attrib['name']
        context = context.replace('dsBetaTestClient::', '')        # Drop dsBetaTestClient:: from context. Factor this out of testthat code.

        # print(context)

        # Split by :: delimiter
        context_parts = context.split('::')

        # Function name
        try:
            function_name = context_parts[0]
            function_name = function_name.replace('()', '')  # Drop the brackets from the function name
            print(function_name)
        except:
            print("ERROR: function name not parsable in: " + context)
            pass

        # Test type
        try:
            test_type = context_parts[1]
            print(test_type)
        except:
            print("ERROR: test type not parsable in: " + context)


        try:
            test_type_extra = context_parts[2]
            print(test_type_extra)
        except:
            print("No extra test type.")


        # Build the dictionary ds_test_status[function_name][test_type]{number, skipped, failures, errors}
        # This should automatically make an entry for each test type specified in the testthat files.
        try:

            # If this test_type is not defined then initiate it for this function_name
            if test_type not in ds_test_status[function_name]:
                ds_test_status[function_name][test_type] = {}
                ds_test_status[function_name][test_type]['number'] = 0
                ds_test_status[function_name][test_type]['skipped'] = 0
                ds_test_status[function_name][test_type]['failures'] = 0
                ds_test_status[function_name][test_type]['errors'] = 0
                ds_test_status[function_name][test_type]['failureText'] = list()


            ds_test_status[function_name][test_type]['number'] += int(testsuite.attrib['tests'])
            ds_test_status[function_name][test_type]['skipped'] += int(testsuite.attrib['skipped'])
            ds_test_status[function_name][test_type]['failures'] += int(testsuite.attrib['failures'])
            ds_test_status[function_name][test_type]['errors'] += int(testsuite.attrib['errors'])

            # Parse the text from the failure notice into the ds_test_status dictionary
            if ds_test_status[function_name][test_type]['failures'] > 0:
                print("\n\nERRORS")
                print(testsuite.tag, testsuite.attrib)
                for testcase in testsuite:
                    print(testcase.tag, testcase.attrib)
                    for failure in testcase:
                        try:
                            print(failure.tag, failure.attrib)
                            print(failure.attrib['message'])
                            print(failure.text)
                            ds_test_status[function_name][test_type]['failureText'].append(failure.text)
                        except:
                            pass
        except:
            pass

    pp.pprint(ds_test_status)


    # Get the coverage
    coverage = parse_coverage(coverage_file_path)

    ################################################################################
    # Make an HTML table of the results.
    # Currently hard coding test types, but could automatically pull these out.
    # print("\n\n##########")

    # Get a list of unique test types, in aphabetical order
    test_types = []
    for this_function in ds_test_status.keys():
        for this_test_type in ds_test_status[this_function].keys():
            test_types.append(this_test_type)

    unique_test_types = sorted(set(test_types))

    h = open(output_file_name, "w")
    h.write('<!DOCTYPE html>\n<html>\n<head>\n<link rel="stylesheet" href="status.css">\n</head>\n<body>')

    h.write("<h2>" + repo_name + "</h2>")
    h.write("Made on " + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    h.write("<table border=1>")

    # Some fixed named columns to beginw with, then use the unique test types derived from the data.
    h.write("<tr><th>Function name</th><th>Coverage</th><th>Smoke test<br/>file exist</th><th>Test file exist</th>")
    for this_unique_test_type in unique_test_types:
        h.write("<th>" + this_unique_test_type + "<br/>pass rate</th>")
    h.write("</tr>")

    for this_function in sorted(ds_test_status.keys()):
        # print('===\n', this_function)

        # Function name with link to repo
        h.write("<tr>")
        h.write('<td><a href="' + remote_repo_path + '/blob/' + branch_name + '/R/' + this_function + '.R" target="_blank">' + this_function + "</a></td>")

        # Coverage columne
        if this_function in coverage:
            this_coverage = float(coverage[this_function])
            if this_coverage > 80:
                h.write('<td class="good">' + str(this_coverage) + '</td>')
            elif this_coverage > 60:
                h.write('<td class="ok">' + str(this_coverage) + '</td>')
            else:
                h.write('<td class="bad">' + str(this_coverage) + '</td>')
        else:
            h.write('<td></td>')

        ####################
        # Smoke test
        # See if test file exists
        expected_test_name = "test-smk-"+this_function+'.R'
        # print(expected_test_name)
        if expected_test_name in ds_tests:
            h.write('<td class="good"><a href="' + remote_repo_path + '/blob/' + branch_name + '/tests/testthat/' + expected_test_name + '" target="_blank">' + expected_test_name + '</a></td>')
        else:
            h.write("<td></td>")

        ####################
        # Other tests
        # See if test exists
        expected_test_name = "test-"+this_function+'.R'
        # print(expected_test_name)
        if expected_test_name in ds_tests:
            h.write('<td class="good"><a href="' + remote_repo_path + '/blob/' + branch_name + '/tests/testthat/' + expected_test_name + '" target="_blank">' + expected_test_name + '</a></td>')
        else:
            h.write("<td></td>")

        # Cycle through all the test types.
        for this_unique_test_type in unique_test_types:
            h.write(calculate_pass_rate(ds_test_status, this_function, this_unique_test_type, gh_log_url))

        h.write("</tr>\n")
    h.write("</table>\n</body>\n</html>")


if __name__ == '__main__':
    main(sys.argv[1:])
