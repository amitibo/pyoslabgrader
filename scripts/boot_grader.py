#!/usr/bin/python
#
# boot_grader
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
    test_folder = DEFAULT_TESTS_FOLDER
    test_path = os.path.join(test_folder, DEFAULT_TEST_NAME)
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
            test_folder, test_name = os.path.split(test_path)
        if o in ("-b", "--break"):
            break_flag = True

    if args:
        submissions_folder = os.path.abspath(args[0])
        
    if not os.path.exists(GRADER_CONFIG_PATH):
        #
        # Init the grader and reboot for starting the test process
        #
        init_grader(submissions_folder, test_path, break_flag, kernel_test=True)
        os.system('reboot')
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
    
    #
    # Process the submission
    #
    if re.search('custom', os.popen("uname -r").read()):
        if break_flag:
            f_results.write("Breaking for manual testing\n")
            f_results.close()
            return
        
        f_results.write("Start of automatic testing\n")

        #
        # In the custom kernel. Run the test.
        #
        test_module = import_path(test_path)
        
        #
        # Load the test status
        #
        test_status = TestStatus()
        
        try:
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
        # Change the grub to custom.
        #
        set_grub(custom=False)
            
    else:
        #
        # Compile and install the new Kernel.
        #
        submission = next_submission(submissions_folder)

        if not submission:
            f_results.write('\n\nFinished checking all submissions\n')
            f_results.close()
            end_grader()
            return

        f_results.write('\n' + 70*'#' + '\nProcessing submission %s\n' % submission)
        
        try:
            #
            # Unzip the submission into a temporary path.
            #
            unzip_submission(submissions_folder, temp_folder, submission, f_results)

            #
            # Handle the compiling and loading of the new kernel
            #
            if os.path.exists(CUSTOM_KERNEL_PATH):
                shutil.rmtree(CUSTOM_KERNEL_PATH)
            shutil.copytree(CUSTOM_KERNEL_BAKCUP_PATH, CUSTOM_KERNEL_PATH)

            #
            # Copy custom modificaions of the grader (memory tracking)
            #
            os.system('cp -rf %s %s' % (os.path.join(BASE_INSTALL_PATH, KERNEL_MODIFICATIONS_FOLDER, '*'), CUSTOM_KERNEL_PATH))
            if os.path.exists(os.path.join(temp_folder, 'Makefile')):
                #
                # Sometimes the students leave a Makefile in the main
                # submission folder.
                #
                os.remove(os.path.join(temp_folder, 'Makefile'))
                
            f_results.write("Start of compilation\n")
            status = os.system(BUILD_SCRIPT + " " + temp_folder)
            if status:
                f_results.flush()
                raise Exception('Failed building the submission, exit with status: %d' % (status/256))

            #
            # Create a test status object.
            # Note:
            # it automatically saves itself on creation.
            #
            TestStatus(new=True)
                
            set_grub(custom=True)

        except:
            traceback.print_exc(file=f_results)
        
    #
    # Handle reboot
    #
    f_results.close()
    os.system('reboot')


if __name__ == '__main__':
    main()
    
