hwgrader
========
A package for writing test for linux_kernel course. This package
contains several modules that simplify writing tests and several
scripts that run them. The main script to run test is 'boot_grader.py'.
Script to handle compilation and testing of a set of submissions.
The script compiles each submission, installs the kernel, reboots
and performs the tests. The reboot and switching between normal
and custom kenrels are handled automatically.

To install the package enter:

    > python setup.py install

To use the 'boot_grader.py' script do the following:

* You should be logged as root.
* Write a test for your assignment. The grader is written in
   python and uses the [unittest][1] package for running the tests.
   Use the file `tests/hw_test.py` as a template.
* Place the zipped submissions under some folder.

To run the test enter:

    > boot_grader.py -t <path-to-test> <path-to-submmisions>

The submissions are unziped one after the other into 'temp' folder
under the submission folder. The results of the run are written into
a log file under the folder 'results' which is also under the
submission folder. The log file is given a unique name which includes
the time of run so it is not overwritten by subsequent runs.

Important Note:
---------------
The build_submission.sh shell script that compiles and installs the
submission assumes the following structure:

    submission.zip
        |
        +-> [sS]ubmitters.txt
        +-> <all source files>

To enable autologin (as root) this script changes several
configuration files, i.e `/etc/inittab`, `/etc/login.defs`, `sysctl.conf`
and `.bash_profile` . It first makes a backup copy of these files
under the folder `/root/temp_grader`. At the end of the run it
restores the original files.

The script also make a 'fresh' copy of the custom kernel between
submissions. The original custom kernel is stored in the temp
folder.

The grader is still in beta state, please send any
comments, ideas or bugs you find to the author: Amit Aides

[1]: http://docs.python.org/release/2.2.1/lib/module-unittest.html
