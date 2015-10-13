import requests
import json
import re
import fileinput

from optparse import OptionParser
import subprocess
import os
import sys
import time

"""

# An evolving thing - takes as input:
- a file which is the output from perfrunner - this file will contain some json which describes the perf results
- the perf keys and expected values

This program parses out the results from the files and compares them against the expected values


"""


def main():
    print 'Starting the perf regression runner'

    usage = '%prog -f conf-file'
    parser = OptionParser(usage)

    parser.add_option('-f', '--filename', dest='filename')
    parser.add_option('-v', '--version', dest='version')

    options, args = parser.parse_args()
    summary = []

    for line in fileinput.input(options.filename):

        time.sleep(10)

        if line[0] == '#' or len(line.strip()) == 0:
            continue

        test, spec, params = line.split()
        print '\n\n', time.asctime( time.localtime(time.time()) ), 'Now running', test
        current_summary = {'test': test, 'output': '', 'result': True}

        test = 'perfSanity/tests/' + test
        spec = 'perfSanity/clusters/' + spec

        my_env = os.environ
        my_env['cluster'] = spec
        my_env['test_config'] = test
        my_env['version'] = options.version
        # proc = subprocess.Popen('ls', env=my_env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        proc = subprocess.Popen('./scripts/setup.sh', env=my_env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                shell=True)

        for line in iter(proc.stdout.readline, ''):
            print 'Setup output', line
            sys.stdout.flush()

        (stdoutdata, stderrdata) = proc.communicate()

        if proc.returncode == 1:
            print '\n\nHave an error during setup'
            print stderrdata
            print stdoutdata
            current_summary['output'] += '  Have an error during setup'
            current_summary['result'] = False
            summary.append(current_summary)
            continue

        print 'Setup complete, starting workload'
        sys.stdout.flush()
        proc = subprocess.Popen('./perfSanity/scripts/workload_dev.sh', env=my_env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        workload_output = ''
        for line in iter(proc.stdout.readline, ''):
            print line
            workload_output += line

        (stdoutdata, stderrdata) = proc.communicate()

        print 'stderrdata', stderrdata

        if proc.returncode == 1:
            print '  Have an error during workload generation'
            current_summary['output'] += '  Have an error during workload generation'
            sys.stdout.flush()
            current_summary['result'] = False
            print stderrdata
            summary.append(current_summary)
            continue

        print '\n\nWorkload complete, analyzing results'
        # parse the line for actual values
        # workload_output = test_workload_output
        p = re.compile(r'Dry run stats: {(.*?)}', re.MULTILINE)
        matches = p.findall(workload_output.replace('\n', ''))

        actual_values = {}
        for m in matches:
            actual = json.loads('{' + m + '}')
            actual_values[actual['metric']] = actual  # ( json.loads('{' + m + '}') )
        print '\n\nWorkload gen output:', workload_output, '\n\n'

        expected_keys = json.loads(params)
        for k in expected_keys.keys():
            if k in actual_values:
                if actual_values[k]['value'] > 1.05 * expected_keys[k]:
                    print '  ', k, ' is greater than expected. Expected', expected_keys[k], 'Actual', actual_values[k][
                        'value']
                    current_summary['output'] += '\n    {0} is greater than expected. Expected {1} actual {2}'.format(k,
                                                                                                                      expected_keys[
                                                                                                                          k],
                                                                                                                      actual_values[
                                                                                                                          k][
                                                                                                                          'value'])
                    current_summary['result'] = False

                elif actual_values[k]['value'] < 0.95 * expected_keys[k]:
                    # sort of want to yellow flag this but for now all we have is a red flag so use that
                    print '  ', k, ' is less than expected. Expected', expected_keys[k], 'Actual', actual_values[k][
                        'value']
                    current_summary['output'] += '\n    {0} is less than expected. Expected {1} actual {2}'.format(k,
                                                                                                                   expected_keys[
                                                                                                                       k],
                                                                                                                   actual_values[
                                                                                                                       k][
                                                                                                                       'value'])
                    current_summary['result'] = False

                del actual_values[k]
            else:
                print '  Expected key', k, ' is not found'
                current_summary['output'] += '\n    Expected key {0} is not found'.format(k)
                current_summary['result'] = False
        if len(actual_values) > 0:
            print '  The following key(s) were present but not expected:'
            for i in actual_values:
                print '    ', i
                current_summary['output'] += '\n    {0} is present but not expected'.format(i)
                current_summary['result'] = False

        summary.append(current_summary)
        print '\nCompleted analysis for', test
        time.sleep(10)
    # end the for loop - print the results
    all_success = True
    print '\n\nResult summary:'
    for i in summary:
        print '\n', i['test'],
        if i['result']:
            print '  ...passed'
        else:
            print i['output']
            all_success = False

    return all_success


if __name__ == "__main__":
    if not main():
        sys.exit(1)