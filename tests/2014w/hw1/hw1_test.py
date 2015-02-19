#!/usr/bin/python

from __future__ import division, generators
from hwgrader.module_utils import *
from hwgrader.test_utils import *
from hwgrader.utils import ParTextTestRunner, ParTestCase, RebootableTestSuite
import fcntl
import unittest
import os
import time
import math
import errno

MODULE_NAME = 'vigenere_module'

DEVICE_NAME = 'vigenere_device'
DEVICE_FILE_PATH = '/dev/vigenere_device'

#
# Calculate the ioctl cmd number
#
MY_MAGIC = 'r'
RESTART = _IOW(MY_MAGIC, 0, 'int')
RESET = _IOW(MY_MAGIC, 1, 'int')
SET_OTHER_PID = _IOW(MY_MAGIC, 2, 'int')

MESSAGE1 = "The Magic Words are Squeamish Ossifrage"
MESSAGE2 = "A man who carries a cat by the tail learns something he can learn in no other way."

DEFAULT_READ_SIZE = 100

SUBMISSION_PATH = '.'

ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'

def cypher(key_phrase, key_index, char, direction=1):
    
    if char not in ALPHABET:
        return char
    
    key = key_phrase[key_index % len(key_phrase)]    
    char_index = ALPHABET.index(char)
    cypher_char = ALPHABET[(char_index + direction*key) % len(ALPHABET)]

    return cypher_char


def cypher_phrase(key, phrase):
    
    key_phrase = [int(i) for i in str(key)]
    phrase = [cypher(key_phrase, key_index, char) for key_index, char in enumerate(phrase)]
    return ''.join(phrase)


def decypher_phrase(key, phrase):
    
    key_phrase = [int(i) for i in str(key)]
    phrase = [cypher(key_phrase, key_index, char, direction=-1) for key_index, char in enumerate(phrase)]
    return ''.join(phrase)
    

class hw_test(ParTestCase):
    """Basic test"""

    _TEST_TIMEOUT = 10
    
    def setUp(self):
        moduleUnload(MODULE_NAME)
        rmDeviceFile(DEVICE_FILE_PATH, silent=True)
        
        moduleLoad(SUBMISSION_PATH, MODULE_NAME)
        createDeviceFile(DEVICE_NAME, DEVICE_FILE_PATH, 0)

    def tearDown(self):
        moduleUnload(MODULE_NAME, silent=False)
        rmDeviceFile(DEVICE_FILE_PATH, silent=False)
    
    def test01(self):
        """Verify that the module was loaded."""

        self.assert_(os.path.exists(DEVICE_FILE_PATH), 'Device not loaded')

    def test02(self):
        """Open/close the 'my_module' device driver"""

        f = os.open(DEVICE_FILE_PATH, os.O_RDWR)
        os.close(f)

    def test03(self):
        """Test the ioctl commands"""
        
        f = os.open(DEVICE_FILE_PATH, os.O_RDWR)
        fcntl.ioctl(f, RESTART)    
        fcntl.ioctl(f, RESET)    
        fcntl.ioctl(f, SET_OTHER_PID, 0)    
        os.close(f)
        
    def test04(self):
        """Check basic writing to the module"""
        
        f = os.open(DEVICE_FILE_PATH, os.O_RDWR)
        
        try:
            actual_size = os.write(f, MESSAGE1)
            expected_size = len(MESSAGE1)
            self.assertEqual(actual_size, expected_size, 'Wrote %d bytes, expected %d' % (actual_size, expected_size))
        finally:
            #
            # Finaly close the file
            #
            os.close(f)
        
    def test05(self):
        """Check basic reading from the module"""
        
        f = os.open(DEVICE_FILE_PATH, os.O_RDWR)
    
        #
        # Test writing and reading
        #
        try:
            actual_size = os.write(f, MESSAGE1)
            expected_size = len(MESSAGE1)
            self.assertEqual(MESSAGE1, os.read(f, expected_size))
        finally:
            #
            # Finaly close the file
            #
            os.close(f)

    def test06(self):
        """Check basic read write between processes"""
        
        f = os.open(DEVICE_FILE_PATH, os.O_RDWR)

        #
        # Fork the parent
        #
        ppid = os.getpid()
        cpid = os.fork()
        if (cpid == 0):
            #
            # In child
            #
            # Set the other_pid
            #
            fcntl.ioctl(f, SET_OTHER_PID, ppid)
            
            #
            # Write the plain text
            #
            os.write(f, MESSAGE1)
    
            #
            # Close the file
            #
            os.close(f)
            
            #
            # Terminate the child process
            #
            os._exit(0)
    
        #
        # In parent
        #
        # Wait for the child to terminate
        #
        os.wait()
        
        #
        # Set the other_pid
        #
        fcntl.ioctl(f, SET_OTHER_PID, cpid)
        
        #
        # Read the text
        #
        self.assertEqual(MESSAGE1, os.read(f, 100))
        
        #
        # Finaly close the file
        #
        os.close(f)
        
    def test07(self):
        """Check basic read write between processes with wrong decoding"""
        
        f = os.open(DEVICE_FILE_PATH, os.O_RDWR)

        #
        # Fork the parent
        #
        ppid = os.getpid()
        cpid = os.fork()
        if (cpid == 0):
            #
            # In child
            #
            # Set the other_pid
            #
            fcntl.ioctl(f, SET_OTHER_PID, ppid)
            
            #
            # Write the plain text
            #
            os.write(f, MESSAGE1)
    
            #
            # Close the file
            #
            os.close(f)
            
            #
            # Terminate the child process
            #
            os._exit(0)
    
        #
        # In parent
        #
        # Wait for the child to terminate
        #
        os.wait()
        
        #
        # Set the other_pid
        #
        fcntl.ioctl(f, SET_OTHER_PID, cpid+1)
        
        #
        # Read the text
        #
        message_read = os.read(f, 100)
        
        #
        # Finaly close the file
        #
        os.close(f)
        
        self.assertEqual(decypher_phrase(ppid+cpid+1, cypher_phrase(ppid+cpid, MESSAGE1)), message_read)

    def test08(self):
        """Check several writes to the buffer"""
        
        f = os.open(DEVICE_FILE_PATH, os.O_RDWR)

        #
        # Fork the parent
        #
        ppid = os.getpid()
        cpid = os.fork()
        if (cpid == 0):
            #
            # In child
            #
            # Set the other_pid
            #
            fcntl.ioctl(f, SET_OTHER_PID, ppid)
            
            #
            # Write the plain text
            #
            os.write(f, MESSAGE1)
    
            #
            # Write a second plain text
            #
            os.write(f, MESSAGE2)
    
            #
            # Close the file
            #
            os.close(f)
            
            #
            # Terminate the child process
            #
            os._exit(0)
    
        #
        # In parent
        #
        # Wait for the child to terminate
        #
        os.wait()
        
        #
        # Set the other_pid
        #
        fcntl.ioctl(f, SET_OTHER_PID, cpid)
        
        #
        # Read the text
        #
        self.assertEqual(MESSAGE1+MESSAGE2, os.read(f, 1000))
        
        #
        # Finaly close the file
        #
        os.close(f)
        
    def test09(self):
        """Check the RESTART command"""
        
        #
        # Open the 'my_moulde' device driver
        #
        f = os.open(DEVICE_FILE_PATH, os.O_RDWR)
    
        #
        # Fork the parent
        #
        fork = tfork2()
        if fork.isChild:
            #
            # In child
            #
            # Set the other_pid
            #
            fcntl.ioctl(f, SET_OTHER_PID, fork.ppid)
            
            #
            # Write the plain text
            #
            os.write(f, MESSAGE1)
            
            #
            # Close the file
            #
            os.close(f)
            
            #
            # Terminate the child process
            #
            fork.exit()
    
        #
        # In parent
        #
        # Wait for the child to release
        #
        fork.wait()
        
        #
        # Set the other_pid
        #
        fcntl.ioctl(f, SET_OTHER_PID, fork.cpid)
        
        #
        # Read the text
        #
        self.assertEqual(MESSAGE1, os.read(f, 100))
        
        #
        # Read the text again, should by empty
        #
        self.assertEqual('', os.read(f, 100))
        
        #
        # Apply the RESTART command
        #
        fcntl.ioctl(f, RESTART)
        
        #
        # Read the text the third time.
        #
        self.assertEqual(MESSAGE1, os.read(f, 100))
        
        #
        # Finaly close the file
        #
        os.close(f)
        
    def test10(self):
        """Check the RESET command"""
        
        #
        # Open the 'my_moulde' device driver
        #
        f = os.open(DEVICE_FILE_PATH, os.O_RDWR)
    
        #
        # Fork the parent
        #
        fork = tfork2()
        if fork.isChild:
            #
            # In child
            #
            # Set the other_pid
            #
            fcntl.ioctl(f, SET_OTHER_PID, fork.ppid)
            
            #
            # Write the plain text
            #
            os.write(f, MESSAGE1)
            
            #
            # Close the file
            #
            os.close(f)
            
            #
            # Terminate the child process
            #
            fork.exit()
    
        #
        # In parent
        #
        # Wait for the child to release
        #
        fork.wait()
        
        #
        # Set the other_pid
        #
        fcntl.ioctl(f, SET_OTHER_PID, fork.cpid)

        #
        # Apply the RESET command
        #
        fcntl.ioctl(f, RESET)
    
        #
        # Read the text, should by empty
        #
        self.assertEqual('', os.read(f, 100))

        #
        # Finaly close the file
        #
        os.close(f)
        
    def test11(self):
        """Check partial read write between processes"""
        
        f = os.open(DEVICE_FILE_PATH, os.O_RDWR)

        #
        # Fork the parent
        #
        ppid = os.getpid()
        cpid = os.fork()
        if (cpid == 0):
            #
            # In child
            #
            # Set the other_pid
            #
            fcntl.ioctl(f, SET_OTHER_PID, ppid)
            
            #
            # Write the plain text
            #
            os.write(f, MESSAGE1)
    
            #
            # Close the file
            #
            os.close(f)
            
            #
            # Terminate the child process
            #
            os._exit(0)
    
        #
        # In parent
        #
        # Wait for the child to terminate
        #
        os.wait()
        
        #
        # Set the other_pid
        #
        fcntl.ioctl(f, SET_OTHER_PID, cpid)
        
        #
        # Read partial text
        #
        self.assertEqual(MESSAGE1[:10], os.read(f, 10))
        
        #
        # Read the rest of the text
        #
        self.assertEqual(MESSAGE1[10:], os.read(f, 100))

        #
        # Finaly close the file
        #
        os.close(f)
        
    def test12(self):
        """Verify correct error handling"""
        
        f = os.open(DEVICE_FILE_PATH, os.O_RDWR)
   
        try:
            #
            # Trying to write 0 bytes
            #
            self.errnoCheck(
                cmd=os.write,
                args=(f, ''),
                expected_errno=errno.EINVAL,
                msg='Writing 0 bytes did not throw OSError'
                )
        finally:
            #
            # Finaly close the file
            #
            os.close(f)


def suite(**args):
    global SUBMISSION_PATH
    
    SUBMISSION_PATH = args['submission_path']
    return unittest.makeSuite(hw_test, prefix='test', suiteClass=RebootableTestSuite)


if __name__ == "__main__":
    unittest.main(testRunner=ParTextTestRunner())
