#!/usr/bin/python
#
# module_grader
# -----------
#
# Author: Amit Aides <amitibo@tx.technion.ac.il>
#

from __future__ import division
import shutil
import getopt
import sys
import re
import os
import time
from hwgrader import *
from hwgrader.utils import *
import ConfigParser
import traceback


def usage(test_path):
    """Print usage details"""
    
    usage_doc = """
Usage: """ + os.path.basename(sys.argv[0]) + """ [options] [path to submission folder]

Initiates the automatic grader. The submissions folder, if not set, defaults to """ + DEFAULT_SUBMISSIONS_FOLDER + """
Options:
  -h, --help        show this help message and exit
  -i, --init        force init of the grader
  -r, --reset       reset the boot files
  -t, --test        set the path to the test file (default """ + test_path + """)
  -b, --break       break after compiling and loading the submission so that the test
                    can be run manually.
"""
    print usage_doc
    

def main():
    """main"""
    
    #
    # Parse the command line
    #
    submissions_folder = DEFAULT_SUBMISSIONS_FOLDER
    test_path = os.path.join(DEFAULT_TESTS_FOLDER, DEFAULT_TEST_NAME)
    break_flag = False

    try:
        opts, args = getopt.getopt(sys.argv[1:], "hirbt:", ["help", "init", "reset", "break", "test="])
    except getopt.GetoptError:
        # print help information and exit:
        usage(test_path)
        sys.exit(2)

    for o, a in opts:
        if o in ("-h", "--help"):
            usage(test_path)
            sys.exit()
        if o in ("-r", "--reset"):
            end_grader()
            return
        if o in ("-i", "--init"):
            if os.path.exists(GRADER_CONFIG_PATH):
                os.remove(GRADER_CONFIG_PATH)
        if o in ("-t", "--test"):
            test_path = os.path.abspath(a)
        if o in ("-b", "--break"):
            break_flag = True

    if args:
        submissions_folder = os.path.abspath(args[0])
        
    if not os.path.exists(GRADER_CONFIG_PATH):
        #
        # Init the grader and reboot for starting the test process
        #
        init_grader(submissions_folder, test_path, break_flag, kernel_test=False)
        os.system('reboot')
        return
    
    if break_flag:
        f_results.write("Breaking for manual testing\n")
        f_results.close()
        return
    
    #
    # Prompt the user in case he wants to end the tests.
    #
    ch = prompt_with_timeout(timeout=5)
    if ch != None:
        print 'Terminating grader'
        end_grader()
        return
    
    #
    # Read the configuration file
    #
    config = ConfigParser.ConfigParser()
    config.read(GRADER_CONFIG_PATH)
    submissions_folder = config.get('paths', 'submissions_folder')
    test_path = config.get('paths', 'test_path')
    results_path = config.get('paths', 'results_path')
    grades_path = config.get('paths', 'grades_path')
    stats_path = config.get('paths', 'stats_path')
    temp_folder = config.get('paths', 'temp_folder')
    break_flag = int(config.get('flags', 'break_flag'))
    
    #
    # Open the result file.
    #
    f_results = open(results_path, 'ab', buffering=0)
    
    try:
        #
        # Load a previous test_status (in cash the test rebooted)
        # or create a new one.
        #
        if os.path.exists(TEST_STATUS_PATH):
            #
            # Continue with the last submission (it probably crashed/rebooted in the middle)
            #
            test_status = TestStatus(path=TEST_STATUS_PATH)
        else:
            #
            # Test a new submission
            #
            test_status = TestStatus(path=TEST_STATUS_PATH, new=True)
            
            #
            # Get next submission.
            #
            submission = next_submission(submissions_folder)
    
            if not submission:
                f_results.write('\n'+70*'#'+'\nFinished checking all submissions\n')
                f_results.close()
                end_grader()
                return
    
            f_results.write('\n'+70*'#'+'\nProcessing submission %s\n' % submission)
            
            unzip_submission(submissions_folder, temp_folder, submission, f_results)
            
            os.chdir(temp_folder)
            if not os.path.exists(os.path.join(temp_folder, MAKE_FILE)):
                test_folder, test_name = os.path.split(test_path)
                shutil.copy(os.path.join(test_folder, MAKE_FILE), temp_folder)
    
            if os.system('make'):
                raise Exception('Failed make of the submission.') 
    
        #
        # Run the test.
        #
        test_module = import_path(test_path)

        test_result = ParTextTestRunner(f_results, verbosity=2, test_status=test_status).run(
            test_module.suite(submission_path=temp_folder, test_path=test_path)
            )
        add_grade(get_submitters(temp_folder), test_result, grades_path)
        add_stats(get_submitters(temp_folder), test_result, stats_path)
    except KeyboardInterrupt:
        f_results.write('Test terminated by user\n')
        f_results.close()
        end_grader()
        return
    except:
        f_results.flush()
        traceback.print_exc(file=f_results)
    
    #
    # Delete the test_status to signal that we
    # finished processing this submission
    #
    os.remove(TEST_STATUS_PATH)
    
    #
    # Handle reboot
    #
    f_results.close()
    os.system('reboot')

if __name__ == '__main__':
    main()
    
