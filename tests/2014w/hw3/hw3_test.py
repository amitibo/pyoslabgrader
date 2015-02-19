#!/usr/bin/python

from __future__ import division
from hwgrader.test_utils import memTrack, tfork, tfork2, compile_extension, ErrnoError, enumerate
from hwgrader.utils import ParTextTestRunner, ParTestCase, RebootableTestSuite
import unittest
import shutil
import sys
import os
import time
import random
import errno


#
# This values are read by the compile_extension function.
#
__module_name__ = 'MPI'
__extension_files__ = ['setup.py', 'py_mpi_messages.c']
__header_file__ = 'mpi_messages_api.h'

EXT_SUCCESSFUL = True

MESSAGE1 = 'Prepare HW2 in time'
MESSAGE1_indexed = 'Prepare HW%d in time'
TEMP_FOLDER = 'temp'

DEFAULT_MESSAGE_SIZE = 100

NULL_TIMEOUT = 1


class MPIerror(Exception):
    def __init__(self, e, msg):
        self.e = e
        self.msg = msg
        
    def __str__(self):
        return '%s %s' % (errno.errorcode[self.e.errno], self.msg)


def send_mpi_message(rank, message):
    try:
        MPI.send_mpi_message(rank, message)
    except OSError, e:
        if e.errno == errno.ENOMEM:
            raise MPIerror(e, '(Out of memory): Failure allocating memory')
        elif e.errno == errno.ESRCH:
            raise MPIerror(e, """(No such process): No such process exists. This can happen in one of three cases:
            1. Either rank, is bigger than the length(-1) of the MPI communication list.
            2. Or that the process with rank, rank, has already terminated.
            3. Or that the sending process is not in the MPI communication list.""")
        elif e.errno == errno.EFAULT:
            raise ErrnoError(e, """(Bad address): Error copying meesage from user space.""")
        elif e.errno == errno.EINVAL:
            raise ErrnoError(e, """(Invalid argument): message is NULL or message_size < 1.""")
        else:
            raise


def register_mpi():
    try:
        rank = MPI.register_mpi()
    except OSError, e:
        if e.errno == errno.ENOMEM:
            raise MPIerror(e, '(Out of memory): Failure allocating memory')
        else:
            raise

    return rank


def receive_mpi_message(rank, timeout, message_size):
    try:
        msg, status = MPI.receive_mpi_message(rank, timeout, message_size)
    except OSError, e:
        if e.errno == errno.ENOMEM:
            raise MPIerror(e, '(Out of memory): Failure allocating memory')
        elif e.errno == errno.ETIMEDOUT:
            raise MPIerror(e, """(Connection timed out): No message from a process with the rank, rank, exists in the message queue of the calling process, and an appropriate message hasn't arrived for timeout time.""")
        elif e.errno == errno.EFAULT:
            raise MPIerror(e, """(Bad address): Error copying message to the user space.""")
        elif e.errno == errno.EINVAL:
            raise ErrnoError(e, """(Invalid argument): message is NULL or message_size < 1.""")
        elif e.errno == errno.ESRCH:
            raise MPIerror(e, """(No such process): No such process exists. This can happen in one of two cases:
            1. Either rank, is bigger than the length(-1) of the MPI communication list.
            2. Or that the receiving process is not in the MPI communication list.
            3. Or that the process with the rank, rank, has terminated before the timeout expiration without sending a message to the receiving process.""")
        else:
            print 'unkown error'
            raise

    return msg, status


class hw_test(ParTestCase):
    """Basic test"""

    def setUp(self):

        pass
    
    def tearDown(self):

        pass

    def verifyMessage(self, rank, timeout, expected_message, strict=False, sleep_time=-1, undersleep_ratio=0.9, oversleep_ratio=1.1):
        """Verify MPI message"""
        
        expected_bytes_number = len(expected_message)

        t0 = time.time()
        rx_message, rx_status = receive_mpi_message(rank, timeout, DEFAULT_MESSAGE_SIZE)
        rx_time = time.time() - t0

        if strict:
            self.assertEqual(rx_status, expected_bytes_number, 'The received number of bytes is not as expected. Received: %d, expected: %d' % (rx_status, expected_bytes_number))
            
        rx_message = rx_message[:expected_bytes_number]
                
        self.assertEqual(expected_message, rx_message, 'The received MPI message is not as expected. Received: %s, expected: %s' % (rx_message, expected_message))

        if sleep_time > 0:
            self.assert_(rx_time > undersleep_ratio*sleep_time, 'The receive time: %.3f [sec], should be bigger than the expected sleep time: %.3f [sec]' % (rx_time, sleep_time))
            self.assert_(rx_time < oversleep_ratio*sleep_time, 'The receive time: %.3f [sec], is bigger than the expected sleep time: %.3f [sec]' % (rx_time, sleep_time))
        
    def test01(self):
        """Verify that the header file compiled successfuly."""

        self.assert_(EXT_SUCCESSFUL, 'Failed compilation of %s.' % __header_file__)
        
    def test02(self):
        """Verify the ability to call the different api commands."""

        #
        # Calling system api's.
        #
        register_mpi()
        send_mpi_message(rank=0, message=MESSAGE1)
        receive_mpi_message(rank=0, timeout=NULL_TIMEOUT, message_size=DEFAULT_MESSAGE_SIZE)
        
    def test03(self):
        """Verify simple self MPI messaging."""

        #
        # Basic write to 'one self'
        #
        register_mpi()
        send_mpi_message(rank=0, message=MESSAGE1)
        
        #
        # Check received message
        #
        self.verifyMessage(rank=0, timeout=NULL_TIMEOUT, expected_message=MESSAGE1)
        
    def test04(self):
        """Verify simple MPI messaging from a (live) child process."""
        
        msg = MESSAGE1_indexed % random.randint(0, 255)
        
        register_mpi()

        fork = tfork2()
        if fork.isChild:
            #
            # In child
            #
            register_mpi()
            send_mpi_message(rank=0, message=msg)

            #
            # Wait for the parent to read message.
            #
            fork.release()
            fork.sync()
            
            #
            # Exit the child
            #
            fork.exit()
            
        #
        # In parent
        # ---------
        # Check received message
        #
        fork.sync()
        self.verifyMessage(rank=1, timeout=NULL_TIMEOUT, expected_message=msg)
        
        #
        # Release the child (to exit)
        #
        fork.release()
        fork.wait()
        
    def test05(self):
        """Verify simple MPI messaging from a (terminated) child process."""
        
        msg = MESSAGE1_indexed % random.randint(0, 255)
        
        register_mpi()

        fork = tfork()
        if fork.isChild:
            #
            # In child
            #
            register_mpi()
            send_mpi_message(rank=0, message=msg)
            
            fork.exit()

        #
        # In parent
        # ---------
        # Wait for the child to exit
        #
        fork.wait()
        
        #
        # Check received message
        #
        self.verifyMessage(rank=1, timeout=NULL_TIMEOUT, expected_message=msg)
        
    def test06(self):
        """Verify simple MPI messaging to a child process."""
        
        msg = MESSAGE1_indexed % random.randint(0, 255)
        
        register_mpi()

        fork = tfork2()
        if fork.isChild:
            #
            # In child
            # ---------
            register_mpi()

            #
            # Allow the parent to send message.
            #
            fork.release()
            fork.sync()
            self.verifyMessage(rank=0, timeout=NULL_TIMEOUT, expected_message=msg)
            
            #
            # Exit the child
            #
            fork.exit()
            
        #
        # In parent
        # ---------
        # Send message
        #
        fork.sync()
        send_mpi_message(1, msg)
        fork.release()
        
        #
        # Release the child (to exit)
        #
        fork.wait()
        
    def test07(self):
        """Verify several MPI messages from a child process."""
        
        MSG_NUM = 100
        msgs = [MESSAGE1_indexed % i for i in range(MSG_NUM)]
        random.shuffle(msgs)
        
        register_mpi()

        fork = tfork2()
        if fork.isChild:
            #
            # In child
            #
            register_mpi()
            
            #
            # Send all messages
            #
            for msg in msgs:
                send_mpi_message(0, msg)
            
            #
            # Allow the 
            #
            fork.release()
            fork.sync()
            
            fork.exit()

        #
        # In parent
        # ---------
        # Release the child
        #
        fork.sync()
        
        #
        # Check received messages
        #
        for msg in msgs:        
            self.verifyMessage(rank=1, timeout=NULL_TIMEOUT, expected_message=msg)

        #
        # Wait for the child to exit
        #
        fork.release()
        fork.wait()
        
    def test08(self):
        """Verify multiple MPI messaging from multiple child processes."""
        
        CHILD_NUM = 100
        MSG_NUM = 10
        msgs = [MESSAGE1_indexed % i for i in range(CHILD_NUM*MSG_NUM)]
        random.shuffle(msgs)
         
        register_mpi()

        forks = []
        for i in range(CHILD_NUM):
            fork = tfork2()
            if fork.isChild:
                #
                # In child
                #
                register_mpi()
                
                #
                # Sync with the parent.
                # This is done so that the rank will be according to the
                # order of child creation
                #
                fork.release()
                
                for j in range(i*MSG_NUM, (i+1)*MSG_NUM):
                    send_mpi_message(0, msgs[j])
                    
                fork.release()
                fork.sync()
                
                fork.exit()
    
            #
            # In parent
            #
            fork.sync()
            forks.append(fork)
     
        #
        # Wait till all child send their messages
        #
        for fork in forks:
            fork.sync()

        #
        # Check if received message
        #
        for i in range(CHILD_NUM):
            #
            # Check received messages
            #
            for j in range(i*MSG_NUM, (i+1)*MSG_NUM):
                self.verifyMessage(rank=i+1, timeout=NULL_TIMEOUT, expected_message=msgs[j])
        
        #
        # Release all childs
        #
        for fork in forks:
            fork.release()
            
        #
        # Wait for childs exit
        #
        for fork in forks:
            fork.wait()

    def test09(self):
        """Verify multiple MPI messaging to multiple child processes."""

        CHILD_NUM = 200
        MSG_NUM = 1000
        msgs = [MESSAGE1_indexed % i for i in range(CHILD_NUM*MSG_NUM)]
        random.shuffle(msgs)
        
        register_mpi()

        forks = []
        for i in range(CHILD_NUM):
            fork = tfork2()
            if fork.isChild:
                #
                # In child
                #
                register_mpi()

                #
                # Sync with the parent.
                # This is done so that the rank will be according to the
                # order of child creation
                #
                fork.release()
                fork.sync()
                
                #
                # Check the received message
                #
                for j in range(i*MSG_NUM, (i+1)*MSG_NUM):
                    self.verifyMessage(rank=0, timeout=NULL_TIMEOUT, expected_message=msgs[j])

                fork.exit()
                
            #
            # In parent
            #
            fork.sync()
            forks.append(fork)
     
        #
        # Send messages to all child processes
        #
        for i in range(CHILD_NUM):
            for j in range(i*MSG_NUM, (i+1)*MSG_NUM):
                send_mpi_message(i+1, msgs[j])

        #
        # Release all childs
        #
        for fork in forks:
            fork.release()
            
        #
        # Wait for childs exit
        #
        for fork in forks:
            fork.wait()

    def test10(self):
        """Verify error handling."""
        
        #
        # Try sending a message from a non registered process
        #
        self.errnoCheck(
            cmd=MPI.send_mpi_message,
            args=(0, MESSAGE1),
            expected_errno=errno.ESRCH,
            msg='Sending a message from a non registered process is not allowed'
            )

        fork = tfork2()
        if fork.isChild:
            #
            # In child
            # Sync with the parent.
            #
            fork.release()
            fork.sync()

            #
            # Try receiving by a non registered process
            #
            self.errnoCheck(
                cmd=MPI.receive_mpi_message,
                args=(0, NULL_TIMEOUT, DEFAULT_MESSAGE_SIZE),
                expected_errno=errno.ESRCH,
                msg='Receiving a message by a non registered process is not allowed'
                )

            register_mpi()
            
            fork.exit()
        
        #
        # In parent
        #
        fork.sync()
        register_mpi()
        
        #
        # Try sending a message to a non existing rank
        #
        self.errnoCheck(
            cmd=MPI.send_mpi_message,
            args=(1, MESSAGE1),
            expected_errno=errno.ESRCH,
            msg='Sending a message to a non existing rank'
            )
        fork.release()
        
        #
        # Wait for the child to exit
        #
        fork.wait()
         
        #
        # Try sending a message to a terminated process
        #
        self.errnoCheck(
            cmd=MPI.send_mpi_message,
            args=(1, MESSAGE1),
            expected_errno=errno.ESRCH,
            msg='Sending a message to a terminated process'
            )

        #
        # Try receiving a non existing message (should cause a timeout)
        #
        self.errnoCheck(
            cmd=MPI.receive_mpi_message,
            args=(0, NULL_TIMEOUT, DEFAULT_MESSAGE_SIZE),
            expected_errno=errno.ETIMEDOUT,
            msg='Cannot receive a non existing message'
            )

    def test11(self):
        """Test correct rank indexing."""
        
        #
        # Open several childs and register them
        #
        CHILD_NUM = 200
       
        forks = []
        for i in range(CHILD_NUM):
            fork = tfork2()
            if fork.isChild:
                #
                # In child, register in synchrnoized order.
                #
                fork.sync()
                rank = register_mpi()
                fork.send(str(rank))

                #
                # Sync with the parent.
                # This is done so that the rank will be according to the
                # order of child creation
                #
                fork.sync()
                fork.exit()

            #
            # In parent
            #
            forks.append(fork)
        
        #
        # Synchronized registration
        #
        ranks = []
        for fork in forks:
            fork.release()
            ranks.append(int(fork.receive()))

        #
        # Wait till all childs exit
        #
        for fork in forks:
            fork.release()
            fork.wait()

        #
        # Verify that the ranks are correctly indexed
        #
        self.assertEqual(ranks, range(CHILD_NUM), 'The processes where rank not in order: %s' % str(ranks))
        
        #
        # verify that the rank index returns to 0
        #
        rank = register_mpi()
        self.assert_(rank == 0, 'Expected reset of rank indexing. Assigned rank: %d' % rank)
        
    def test12(self):
        """Test correct memory handling - release memory when exiting a process."""
        
        mm_track = memTrack()
        MSG_NUM = 10
        
        try:
            mm_track.start_track()
                
            fork = tfork()
            if fork.isChild:
                #
                # In child:
                # Register and send self several messages
                #
                register_mpi()
                for i in range(MSG_NUM):
                    send_mpi_message(0, MESSAGE1_indexed % i)
                
                fork.exit()
    
            fork.wait()
    
            mm_track.end_track()
            
            mm_track.validate((fork.ppid, fork.cpid), self, debug=True)
            
        finally:
            mm_track.close()

    def test13(self):
        """Test correct timeout handling (timeout doesn't happen)"""
        SLEEP_TIME = 2
        
        MPI.register_mpi()
        
        #
        # Fork the parent
        #
        fork = tfork2()
        if fork.isChild:
            #
            # In child
            #
            MPI.register_mpi()
            fork.release()
            
            time.sleep(SLEEP_TIME)
            
            MPI.send_mpi_message(rank=0, message=MESSAGE1)
            
            #
            # Exit the child
            #
            fork.exit()
            
        #
        # In parent
        # ---------
        # Check received message
        #
        fork.sync()
        
        #
        # Verify message and sleep time.
        #
        self.verifyMessage(rank=1, timeout=2*SLEEP_TIME, expected_message=MESSAGE1, sleep_time=SLEEP_TIME)
        
        #
        # Wait for the child to terminate
        #
        fork.wait()

    def test14(self):
        """Test correct timeout handling (timeout happens)"""
        SLEEP_TIME = 2
        
        MPI.register_mpi()
        
        #
        # Fork the parent
        #
        fork = tfork2()
        if fork.isChild:
            #
            # In child
            #
            MPI.register_mpi()
            fork.release()
            
            time.sleep(SLEEP_TIME)
            MPI.send_mpi_message(rank=0, message=MESSAGE1)
            
            #
            # Exit the child
            #
            fork.exit()
            
        #
        # In parent
        # ---------
        # Check received message
        #
        fork.sync()
        
        #
        # Verify message and sleep time.
        #
        self.errnoCheck(
            cmd=MPI.receive_mpi_message,
            args=(1, .8*SLEEP_TIME, DEFAULT_MESSAGE_SIZE),
            expected_errno=errno.ETIMEDOUT,
            msg='The receive_mpi_message call should have timed out, but it did not'
            )

        #
        # Wait for the child to terminate
        #
        fork.wait()

    def test15(self):
        """Verify multiple timeouts."""

        CHILD_NUM = 10
        delta_times = [random.random()*2 for i in range(CHILD_NUM)]
        sleep_times = [delta_times[0]]
        for i in range(1, CHILD_NUM):
            sleep_times.append(sleep_times[i-1]+delta_times[i])
        timeout_time = int(sleep_times[-1]*2)
        register_mpi()

        forks = []
        for i in range(CHILD_NUM):
            fork = tfork2()
            if fork.isChild:
                #
                # In child
                #
                register_mpi()

                #
                # Sync with the parent.
                # This is done so that the rank will be according to the
                # order of child creation
                #
                fork.release()
                fork.sync()
                
                #
                # Check the received message
                #
                self.verifyMessage(
                    rank=0,
                    timeout=timeout_time,
                    expected_message=MESSAGE1_indexed % i,
                    sleep_time=sleep_times[i]
                )

                fork.exit()
                
            #
            # In parent
            #
            fork.sync()
            forks.append(fork)
     
        #
        # Release all childs
        #
        for fork in forks:
            fork.release()
            
        #
        # Send messages to all child processes
        #
        for i in range(CHILD_NUM):
            time.sleep(delta_times[i])
            send_mpi_message(i+1, MESSAGE1_indexed % i)

        #
        # Wait for childs exit
        #
        for fork in forks:
            fork.wait()


def suite(**args):
    
    global EXT_SUCCESSFUL
    
    #
    # First, compile the extension
    #
    test_folder = os.path.split(args['test_path'])[0]
    submission_folder = args['submission_path']
    EXT_SUCCESSFUL = compile_extension(
        test_folder=test_folder,
        submission_folder=submission_folder,
        _globals=globals()
    )

    #
    # Return the test suite
    #
    return unittest.makeSuite(hw_test, prefix='test', suiteClass=RebootableTestSuite)


if __name__ == "__main__":

    script_path = os.path.abspath(sys.argv[0])
    test_folder = os.path.split(script_path)[0]
    submission_folder = test_folder
    
    #
    # Compile the extension
    #
    compile_extension(
        test_folder=test_folder,
        submission_folder=submission_folder,
        _globals=globals()
    )

    #
    # Run the tests
    #
    unittest.main(testRunner=ParTextTestRunner())
